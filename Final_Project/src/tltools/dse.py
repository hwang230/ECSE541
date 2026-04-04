from __future__ import annotations

import csv
import itertools
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .runner import timeloop_model_metrics
from .scalesim_runner import run_scalesim_gemm

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")
_SUMMARY_DROP_COLUMNS = {
    "status",
    "stderr_tail",
    "utilization",
    "local_buffer_bw",
    "local_buffer_depth",
    "area_um2_art_sum",
}
_POINT_FIELDS = (
    "pe_x",
    "pe_y",
    "global_buffer_depth",
    "local_buffer_depth",
    "backing_storage_bw",
    "local_buffer_bw",
)
_SHARED_POINT_KEYS = (
    "global_buffer_depth",
    "local_buffer_depth",
    "backing_storage_bw",
    "local_buffer_bw",
)


@dataclass(frozen=True)
class SweepPoint:
    pe_x: int
    pe_y: int
    global_buffer_depth: int
    local_buffer_depth: int
    backing_storage_bw: int
    local_buffer_bw: int

    @property
    def pe_count(self) -> int:
        return self.pe_x * self.pe_y


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _render_template(template_text: str, values: dict[str, Any]) -> str:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

    leftovers = sorted(set(_PLACEHOLDER_RE.findall(rendered)))
    if leftovers:
        keys = ", ".join(leftovers)
        raise ValueError(f"Unresolved template keys: {keys}")

    return rendered


def _sanitize_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)
    return safe.strip("_")


def _coerce_sweep_values(value: Any) -> list[int]:
    if isinstance(value, list):
        return [int(x) for x in value]
    return [int(value)]


def _missing_sweep_keys(sweep: dict[str, Any], fixed: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if key not in sweep and key not in fixed]


def _merged_sweep_values(sweep: dict[str, Any], fixed: dict[str, Any], key: str) -> list[int]:
    if key in sweep:
        return _coerce_sweep_values(sweep[key])
    if key in fixed:
        return _coerce_sweep_values(fixed[key])
    raise ValueError(f"Missing sweep key: {key}")


def _expand_points(sweep: dict[str, Any], fixed: dict[str, Any] | None = None) -> list[SweepPoint]:
    fixed = fixed or {}

    if "pe_dim" in sweep or "pe_dim" in fixed:
        points: list[SweepPoint] = []
        pe_dims = _merged_sweep_values(sweep, fixed, "pe_dim")
        missing = _missing_sweep_keys(sweep, fixed, _SHARED_POINT_KEYS)
        if missing:
            raise ValueError(f"Missing sweep keys: {', '.join(missing)}")

        for pe_dim, gb, lb, b_bw, l_bw in itertools.product(
            pe_dims,
            *(_merged_sweep_values(sweep, fixed, key) for key in _SHARED_POINT_KEYS),
        ):
            points.append(
                SweepPoint(
                    pe_x=int(pe_dim),
                    pe_y=int(pe_dim),
                    global_buffer_depth=int(gb),
                    local_buffer_depth=int(lb),
                    backing_storage_bw=int(b_bw),
                    local_buffer_bw=int(l_bw),
                )
            )
        return points

    missing = _missing_sweep_keys(sweep, fixed, _POINT_FIELDS)
    if missing:
        raise ValueError(f"Missing sweep keys: {', '.join(missing)}")

    points: list[SweepPoint] = []
    for values in itertools.product(*(_merged_sweep_values(sweep, fixed, key) for key in _POINT_FIELDS)):
        points.append(
            SweepPoint(
                pe_x=int(values[0]),
                pe_y=int(values[1]),
                global_buffer_depth=int(values[2]),
                local_buffer_depth=int(values[3]),
                backing_storage_bw=int(values[4]),
                local_buffer_bw=int(values[5]),
            )
        )
    return points


def _area_proxy_um2(point: SweepPoint, constants: dict[str, Any]) -> float:
    """
    Fast area proxy for design ranking when ART area is unavailable/flat.

    The proxy uses configurable per-unit coefficients and architecture sizes:
      total = PE_MACC_area + LocalBuffer_area + GlobalBuffer_area
    """
    datawidth = int(constants.get("datawidth", 8))
    global_width = int(constants.get("global_buffer_width", 32))
    macc_unit_area_um2 = float(constants.get("proxy_macc_area_um2", 300.0))
    rf_bit_area_um2 = float(constants.get("proxy_rf_bit_area_um2", 0.08))
    sram_bit_area_um2 = float(constants.get("proxy_sram_bit_area_um2", 0.04))

    pe_area = point.pe_count * macc_unit_area_um2
    local_bits = point.pe_count * point.local_buffer_depth * datawidth
    global_bits = point.global_buffer_depth * global_width
    memory_area = local_bits * rf_bit_area_um2 + global_bits * sram_bit_area_um2
    return pe_area + memory_area


def _parse_stats_summary(stats_path: Path) -> dict[str, float]:
    if not stats_path.exists():
        return {}

    text = stats_path.read_text(encoding="utf-8")
    out: dict[str, float] = {}

    patterns = {
        "summary_utilization_percent": r"^Utilization:\s*([0-9.eE+-]+)%$",
        "summary_cycles": r"^Cycles:\s*([0-9]+)$",
        "summary_energy_uj": r"^Energy:\s*([0-9.eE+-]+)\s*uJ$",
        "summary_edp_j_cycle": r"^EDP\(J\*cycle\):\s*([0-9.eE+-]+)$",
        "summary_area_mm2": r"^Area:\s*([0-9.eE+-]+)\s*mm\^2$",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.MULTILINE)
        if match:
            value = float(match.group(1))
            out[key] = int(value) if key == "summary_cycles" else value

    throttles = re.findall(r"Bandwidth throttling\s*:\s*([0-9.eE+-]+)", text)
    if throttles:
        vals = [float(x) for x in throttles]
        out["bandwidth_throttling_min"] = min(vals)
        out["bandwidth_throttling_max"] = max(vals)

    return out


def _round_summary_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 2)
    return value


def _round_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _round_summary_value(value) for key, value in row.items()}


def _resolve_config_path(config_path: Path, configured_path: str | Path) -> Path:
    path = Path(configured_path)
    return path if path.is_absolute() else (config_path.parent / path).resolve()


def _write_if_needed(path: Path, text: str, overwrite: bool) -> None:
    if overwrite or not path.exists():
        path.write_text(text, encoding="utf-8")


def _load_existing_rows(csv_path: Path) -> dict[str, dict[str, Any]]:
    if not csv_path.exists():
        return {}

    existing_rows: dict[str, dict[str, Any]] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            run_name = str(row.get("run_name", "")).strip()
            if run_name:
                for col in _SUMMARY_DROP_COLUMNS:
                    row.pop(col, None)
                existing_rows[run_name] = row
    return existing_rows


def _simulator_backend(config: dict[str, Any]) -> str:
    backend = str(config.get("simulator", "timeloop")).strip().lower()
    aliases = {
        "timeloop+accelergy": "timeloop",
        "timeloop_accelergy": "timeloop",
        "timeloop": "timeloop",
        "scalesim": "scalesim",
        "scale-sim": "scalesim",
    }
    normalized = aliases.get(backend)
    if normalized is None:
        raise ValueError(f"Unsupported simulator backend: {backend}")
    return normalized


def _scalesim_buffer_sizes_kb(point: SweepPoint, constants: dict[str, Any]) -> tuple[int, int, int]:
    datawidth = int(constants.get("datawidth", 8))
    global_width = int(constants.get("global_buffer_width", 32))

    global_bytes = point.global_buffer_depth * global_width // 8
    local_bytes_total = point.pe_count * point.local_buffer_depth * datawidth // 8

    ifmap_sram_kb = max(1, int(constants.get("scalesim_ifmap_sram_kb", max(1, global_bytes // 1024))))
    filter_sram_kb = max(
        1,
        int(constants.get("scalesim_filter_sram_kb", max(1, local_bytes_total // 1024))),
    )
    ofmap_sram_kb = max(1, int(constants.get("scalesim_ofmap_sram_kb", max(1, global_bytes // 1024))))
    return ifmap_sram_kb, filter_sram_kb, ofmap_sram_kb


def _run_timeloop_point(
    *,
    run_dir: Path,
    point: SweepPoint,
    constants: dict[str, Any],
    clock_seconds: float,
    timeout_seconds: int,
    overwrite_inputs: bool,
    template_text: str,
    problem_template_text: str,
    mapping_template_text: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    problem_m = int(constants.get("problem_m", 64))
    problem_n = int(constants.get("problem_n", 64))
    problem_k = int(constants.get("problem_k", 64))
    k_tile = int(constants.get("k_tile", 1))
    if problem_m % point.pe_x != 0 or problem_n % point.pe_y != 0:
        raise ValueError(
            f"Problem dimensions (M={problem_m}, N={problem_n}) must be divisible by "
            f"PE dims ({point.pe_x}, {point.pe_y})."
        )
    if k_tile <= 0:
        raise ValueError("k_tile must be > 0.")
    if problem_k % k_tile != 0:
        raise ValueError(f"problem_k ({problem_k}) must be divisible by k_tile ({k_tile}).")

    top_m_factor = problem_m // point.pe_x
    top_n_factor = problem_n // point.pe_y
    top_k_outer_factor = problem_k // k_tile

    values = {
        **{k.upper(): v for k, v in constants.items()},
        "PE_X": point.pe_x,
        "PE_Y": point.pe_y,
        "PE_COUNT": point.pe_count,
        "PE_COUNT_MINUS_1": point.pe_count - 1,
        "PROBLEM_M": problem_m,
        "PROBLEM_N": problem_n,
        "PROBLEM_K": problem_k,
        "TOP_M_FACTOR": top_m_factor,
        "TOP_N_FACTOR": top_n_factor,
        "TOP_K_FACTOR": problem_k,
        "TOP_K_OUTER_FACTOR": top_k_outer_factor,
        "K_TILE": k_tile,
        "GLOBAL_BUFFER_DEPTH": point.global_buffer_depth,
        "LOCAL_BUFFER_DEPTH": point.local_buffer_depth,
        "BACKING_STORAGE_BW": point.backing_storage_bw,
        "LOCAL_BUFFER_BW": point.local_buffer_bw,
    }

    arch_text = _render_template(template_text, values)
    problem_text = _render_template(problem_template_text, values)
    mapping_text = _render_template(mapping_template_text, values)
    arch_path = run_dir / "arch.yaml"
    problem_path_out = run_dir / "problem.yaml"
    mapping_path_out = run_dir / "mapping.yaml"
    _write_if_needed(arch_path, arch_text, overwrite_inputs)
    _write_if_needed(problem_path_out, problem_text, overwrite_inputs)
    _write_if_needed(mapping_path_out, mapping_text, overwrite_inputs)

    result = timeloop_model_metrics(
        "arch.yaml",
        "problem.yaml",
        "mapping.yaml",
        cwd=run_dir,
        clock_seconds=clock_seconds,
        timeout=timeout_seconds,
    )
    stats_summary = _parse_stats_summary(run_dir / "timeloop-model.stats.txt")
    metrics = result.get("metrics", {})
    row: dict[str, Any] = {
        "simulator": "timeloop",
        "returncode": result["returncode"],
        "cycles": metrics.get("cycles"),
        "latency_ns": metrics.get("latency_ns"),
        "pj_per_compute": metrics.get("pj_per_compute"),
        "pj_per_algorithmic_compute": metrics.get("pj_per_algorithmic_compute"),
        "summary_cycles": None,
        "summary_utilization_percent": None,
        "summary_energy_uj": None,
        "summary_edp_j_cycle": None,
        "summary_area_mm2": None,
        "bandwidth_throttling_min": None,
        "bandwidth_throttling_max": None,
    }
    row.update(stats_summary)
    return row, result


def _run_scalesim_point(
    *,
    run_dir: Path,
    point: SweepPoint,
    constants: dict[str, Any],
    clock_seconds: float,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    problem_m = int(constants.get("problem_m", 64))
    problem_n = int(constants.get("problem_n", 64))
    problem_k = int(constants.get("problem_k", 64))
    dataflow = str(constants.get("scalesim_dataflow", "ws")).strip().lower()
    bandwidth_value = int(constants.get("scalesim_operand_bw", point.backing_storage_bw))
    bandwidths = tuple(
        int(x)
        for x in constants.get(
            "scalesim_bandwidths",
            [bandwidth_value, bandwidth_value, bandwidth_value],
        )
    )
    if len(bandwidths) != 3:
        raise ValueError("scalesim_bandwidths must contain exactly 3 integer values.")

    ifmap_sram_kb, filter_sram_kb, ofmap_sram_kb = _scalesim_buffer_sizes_kb(point, constants)
    result = run_scalesim_gemm(
        run_dir=run_dir,
        m=problem_m,
        n=problem_n,
        k=problem_k,
        array_rows=point.pe_x,
        array_cols=point.pe_y,
        ifmap_sram_kb=ifmap_sram_kb,
        filter_sram_kb=filter_sram_kb,
        ofmap_sram_kb=ofmap_sram_kb,
        dataflow=dataflow,
        bandwidths=bandwidths,
        clock_seconds=clock_seconds,
        timeout=timeout_seconds,
    )
    metrics = result.metrics
    row: dict[str, Any] = {
        "simulator": "scalesim",
        "returncode": result.returncode,
        "cycles": metrics.get("total_cycles"),
        "latency_ns": metrics.get("latency_ns"),
        "summary_cycles": metrics.get("total_cycles"),
        "summary_utilization_percent": metrics.get("overall_utilization_percent"),
        "summary_stall_cycles": metrics.get("stall_cycles"),
        "summary_mapping_efficiency_percent": metrics.get("mapping_efficiency_percent"),
        "summary_compute_utilization_percent": metrics.get("compute_utilization_percent"),
        "summary_total_cycles_incl_prefetch": metrics.get("total_cycles_incl_prefetch"),
        "avg_ifmap_sram_bw": metrics.get("avg_ifmap_sram_bw"),
        "avg_filter_sram_bw": metrics.get("avg_filter_sram_bw"),
        "avg_ofmap_sram_bw": metrics.get("avg_ofmap_sram_bw"),
        "avg_ifmap_dram_bw": metrics.get("avg_ifmap_dram_bw"),
        "avg_filter_dram_bw": metrics.get("avg_filter_dram_bw"),
        "avg_ofmap_dram_bw": metrics.get("avg_ofmap_dram_bw"),
        "dram_ifmap_reads": metrics.get("dram_ifmap_reads"),
        "dram_filter_reads": metrics.get("dram_filter_reads"),
        "dram_ofmap_writes": metrics.get("dram_ofmap_writes"),
        "scalesim_ifmap_sram_kb": ifmap_sram_kb,
        "scalesim_filter_sram_kb": filter_sram_kb,
        "scalesim_ofmap_sram_kb": ofmap_sram_kb,
        "scalesim_dataflow": dataflow,
    }
    return row, {"returncode": result.returncode}


def run_dse(config_path: str | Path) -> Path:
    config = _load_yaml(config_path)
    config_path = Path(config_path).resolve()
    backend = _simulator_backend(config)

    out_root = Path(config.get("out_dir", "src/results/dse_runs"))
    if not out_root.is_absolute():
        out_root = (config_path.parent / out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    clock_seconds = float(config.get("clock_seconds", 1e-9))
    timeout_seconds = int(config.get("timeout_seconds", 120))
    keep_failed_runs = bool(config.get("keep_failed_runs", True))
    resume_existing = bool(config.get("resume_existing", True))
    overwrite_inputs = bool(config.get("overwrite_inputs", False))
    constants = dict(config.get("constants", {}))
    fixed = dict(config.get("fixed", {}))

    template_text = ""
    problem_template_text = ""
    mapping_template_text = ""
    if backend == "timeloop":
        arch_template_path = _resolve_config_path(config_path, config["arch_template"])
        problem_path = _resolve_config_path(config_path, config["problem"])
        mapping_path = _resolve_config_path(config_path, config["mapping"])

        template_text = arch_template_path.read_text(encoding="utf-8")
        problem_template_text = problem_path.read_text(encoding="utf-8")
        mapping_template_text = mapping_path.read_text(encoding="utf-8")
    points = _expand_points(config["sweep"], fixed)

    rows: list[dict[str, Any]] = []
    csv_path = out_root / "summary.csv"
    existing_rows_by_name = _load_existing_rows(csv_path) if resume_existing else {}

    for idx, point in enumerate(points, start=1):
        run_name = _sanitize_name(
            f"pt{idx:03d}_pe{point.pe_x}x{point.pe_y}_gb{point.global_buffer_depth}_lb{point.local_buffer_depth}_"
            f"bbw{point.backing_storage_bw}_lbw{point.local_buffer_bw}"
        )

        if resume_existing and run_name in existing_rows_by_name:
            rows.append(existing_rows_by_name[run_name])
            continue

        run_dir = out_root / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        if backend == "timeloop":
            backend_row, result = _run_timeloop_point(
                run_dir=run_dir,
                point=point,
                constants=constants,
                clock_seconds=clock_seconds,
                timeout_seconds=timeout_seconds,
                overwrite_inputs=overwrite_inputs,
                template_text=template_text,
                problem_template_text=problem_template_text,
                mapping_template_text=mapping_template_text,
            )
        else:
            backend_row, result = _run_scalesim_point(
                run_dir=run_dir,
                point=point,
                constants=constants,
                clock_seconds=clock_seconds,
                timeout_seconds=timeout_seconds,
            )

        row: dict[str, Any] = {
            "run_name": run_name,
            "pe_x": point.pe_x,
            "pe_y": point.pe_y,
            "pe_count": point.pe_count,
            "global_buffer_depth": point.global_buffer_depth,
            "local_buffer_depth": point.local_buffer_depth,
            "backing_storage_bw": point.backing_storage_bw,
            "local_buffer_bw": point.local_buffer_bw,
            "area_proxy_um2": _area_proxy_um2(point, constants),
        }
        row.update(backend_row)
        for col in _SUMMARY_DROP_COLUMNS:
            row.pop(col, None)

        rows.append(row)

        if row["returncode"] != 0 and not keep_failed_runs:
            shutil.rmtree(run_dir, ignore_errors=True)

    rows = [_round_summary_row(row) for row in rows]
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path
