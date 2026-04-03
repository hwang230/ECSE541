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

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")
_SUMMARY_DROP_COLUMNS = {
    "status",
    "stderr_tail",
    "utilization",
    "local_buffer_bw",
    "local_buffer_depth",
    "area_um2_art_sum",
}


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
        required = [
            "global_buffer_depth",
            "local_buffer_depth",
            "backing_storage_bw",
            "local_buffer_bw",
        ]
        missing = [k for k in required if k not in sweep and k not in fixed]
        if missing:
            raise ValueError(f"Missing sweep keys: {', '.join(missing)}")

        for pe_dim, gb, lb, b_bw, l_bw in itertools.product(
            pe_dims,
            _merged_sweep_values(sweep, fixed, "global_buffer_depth"),
            _merged_sweep_values(sweep, fixed, "local_buffer_depth"),
            _merged_sweep_values(sweep, fixed, "backing_storage_bw"),
            _merged_sweep_values(sweep, fixed, "local_buffer_bw"),
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

    required = [
        "pe_x",
        "pe_y",
        "global_buffer_depth",
        "local_buffer_depth",
        "backing_storage_bw",
        "local_buffer_bw",
    ]
    missing = [k for k in required if k not in sweep and k not in fixed]
    if missing:
        raise ValueError(f"Missing sweep keys: {', '.join(missing)}")

    points: list[SweepPoint] = []
    for values in itertools.product(*(_merged_sweep_values(sweep, fixed, key) for key in required)):
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


def run_dse(config_path: str | Path) -> Path:
    config = _load_yaml(config_path)
    config_path = Path(config_path).resolve()

    out_root = Path(config.get("out_dir", "src/results/dse_runs"))
    if not out_root.is_absolute():
        out_root = (config_path.parent / out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    arch_template_path = Path(config["arch_template"])
    if not arch_template_path.is_absolute():
        arch_template_path = (config_path.parent / arch_template_path).resolve()

    problem_path = Path(config["problem"])
    if not problem_path.is_absolute():
        problem_path = (config_path.parent / problem_path).resolve()

    mapping_path = Path(config["mapping"])
    if not mapping_path.is_absolute():
        mapping_path = (config_path.parent / mapping_path).resolve()

    clock_seconds = float(config.get("clock_seconds", 1e-9))
    timeout_seconds = int(config.get("timeout_seconds", 120))
    keep_failed_runs = bool(config.get("keep_failed_runs", True))
    resume_existing = bool(config.get("resume_existing", True))
    overwrite_inputs = bool(config.get("overwrite_inputs", False))
    constants = dict(config.get("constants", {}))
    fixed = dict(config.get("fixed", {}))

    template_text = arch_template_path.read_text(encoding="utf-8")
    problem_template_text = problem_path.read_text(encoding="utf-8")
    mapping_template_text = mapping_path.read_text(encoding="utf-8")
    points = _expand_points(config["sweep"], fixed)

    rows: list[dict[str, Any]] = []
    existing_rows_by_name: dict[str, dict[str, Any]] = {}
    csv_path = out_root / "summary.csv"
    if resume_existing and csv_path.exists():
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                run_name = str(row.get("run_name", "")).strip()
                if run_name:
                    for col in _SUMMARY_DROP_COLUMNS:
                        row.pop(col, None)
                    existing_rows_by_name[run_name] = row

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
        if overwrite_inputs or not arch_path.exists():
            arch_path.write_text(arch_text, encoding="utf-8")
        if overwrite_inputs or not problem_path_out.exists():
            problem_path_out.write_text(problem_text, encoding="utf-8")
        if overwrite_inputs or not mapping_path_out.exists():
            mapping_path_out.write_text(mapping_text, encoding="utf-8")

        result = timeloop_model_metrics(
            "arch.yaml",
            "problem.yaml",
            "mapping.yaml",
            cwd=run_dir,
            clock_seconds=clock_seconds,
            timeout=timeout_seconds,
        )
        metrics = result.get("metrics", {})
        outputs = result.get("outputs", {})
        stats_summary = _parse_stats_summary(run_dir / "timeloop-model.stats.txt")

        row: dict[str, Any] = {
            "run_name": run_name,
            "returncode": result["returncode"],
            "pe_x": point.pe_x,
            "pe_y": point.pe_y,
            "pe_count": point.pe_count,
            "global_buffer_depth": point.global_buffer_depth,
            "backing_storage_bw": point.backing_storage_bw,
            "cycles": metrics.get("cycles"),
            "latency_ns": metrics.get("latency_ns"),
            "pj_per_compute": metrics.get("pj_per_compute"),
            "pj_per_algorithmic_compute": metrics.get("pj_per_algorithmic_compute"),
            "area_proxy_um2": _area_proxy_um2(point, constants),
            "summary_cycles": None,
            "summary_utilization_percent": None,
            "summary_energy_uj": None,
            "summary_edp_j_cycle": None,
            "summary_area_mm2": None,
            "bandwidth_throttling_min": None,
            "bandwidth_throttling_max": None,
        }
        row.update(stats_summary)
        for col in _SUMMARY_DROP_COLUMNS:
            row.pop(col, None)

        rows.append(row)

        if row["returncode"] != 0 and not keep_failed_runs:
            shutil.rmtree(run_dir, ignore_errors=True)

    fieldnames = sorted({k for row in rows for k in row.keys()})
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path
