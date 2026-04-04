from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

CORE_METRICS = ("latency", "energy", "area", "utilization")
RANKING_METRICS = CORE_METRICS + ("pj_per_compute", "summary_energy_uj", "summary_edp_j_cycle")


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _utilization_percent(row: dict[str, Any]) -> float | None:
    util = _to_float(row.get("summary_utilization_percent"))
    if util is None:
        throttle = _to_float(row.get("bandwidth_throttling_max"))
        if throttle is None:
            return None
        util = throttle * 100.0
    return max(0.0, min(100.0, util))


def _ok_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        status = str(row.get("status", "")).strip().lower()
        if status:
            if status == "ok":
                out.append(row)
            continue
        rc = _to_float(row.get("returncode"))
        if rc is None or int(rc) == 0:
            out.append(row)
    return out


def _metric_value(row: dict[str, Any], metric: str) -> float | None:
    if metric == "latency":
        return _to_float(row.get("summary_cycles")) or _to_float(row.get("cycles")) or _to_float(
            row.get("latency_ns")
        )
    if metric == "energy":
        return _to_float(row.get("summary_energy_uj")) or _to_float(row.get("pj_per_compute"))
    if metric == "area":
        return (
            _to_float(row.get("area_proxy_um2"))
            or _to_float(row.get("summary_area_mm2"))
            or _to_float(row.get("area_um2_art_sum"))
        )
    if metric == "utilization":
        return _utilization_percent(row)
    return _to_float(row.get(metric))


def _sorted_top(rows: list[dict[str, Any]], key: str, topk: int) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        val = _metric_value(row, key)
        if val is not None:
            scored.append((val, row))
    reverse = key == "utilization"
    scored.sort(key=lambda x: x[0], reverse=reverse)
    return [r for _, r in scored[:topk]]


def _dominates(a: dict[str, Any], b: dict[str, Any], metrics: tuple[str, ...]) -> bool:
    dirs = {
        "latency": "min",
        "energy": "min",
        "area": "min",
        "utilization": "max",
    }
    a_vals = [_metric_value(a, m) for m in metrics]
    b_vals = [_metric_value(b, m) for m in metrics]
    if any(v is None for v in a_vals + b_vals):
        return False

    not_worse_all = True
    strictly_better_any = False
    for i, metric in enumerate(metrics):
        av = float(a_vals[i])
        bv = float(b_vals[i])
        if dirs.get(metric, "min") == "max":
            if av < bv:
                not_worse_all = False
                break
            if av > bv:
                strictly_better_any = True
        else:
            if av > bv:
                not_worse_all = False
                break
            if av < bv:
                strictly_better_any = True
    return not_worse_all and strictly_better_any


def _pareto_front(rows: list[dict[str, Any]], metrics: tuple[str, ...]) -> list[dict[str, Any]]:
    front: list[dict[str, Any]] = []
    for cand in rows:
        cand_vals = [_metric_value(cand, m) for m in metrics]
        if any(v is None for v in cand_vals):
            continue

        dominated = False
        kept: list[dict[str, Any]] = []
        for kept_row in front:
            if _dominates(kept_row, cand, metrics):
                dominated = True
                break
            if not _dominates(cand, kept_row, metrics):
                kept.append(kept_row)
        if not dominated:
            kept.append(cand)
            front = kept

    front.sort(
        key=lambda r: (
            _metric_value(r, "latency") if _metric_value(r, "latency") is not None else float("inf"),
            _metric_value(r, "energy") if _metric_value(r, "energy") is not None else float("inf"),
            _metric_value(r, "area") if _metric_value(r, "area") is not None else float("inf"),
            -(
                _metric_value(r, "utilization")
                if _metric_value(r, "utilization") is not None
                else float("-inf")
            ),
        )
    )
    return front


def _print_table(title: str, rows: list[dict[str, Any]]) -> None:
    print(f"\n{title}")
    print("run_name, pe_x, pe_y, gb, bbw, cycles, energy, area_proxy, util%")
    for row in rows:
        print(
            f"{row.get('run_name')}, {row.get('pe_x')}, {row.get('pe_y')}, "
            f"{row.get('global_buffer_depth')}, {row.get('backing_storage_bw')}, "
            f"{row.get('summary_cycles') or row.get('cycles')}, "
            f"{row.get('summary_energy_uj') or row.get('pj_per_compute')}, "
            f"{row.get('area_proxy_um2') or row.get('summary_area_mm2')}, "
            f"{_utilization_percent(row)}"
        )


def _parse_metric_list(text: str) -> tuple[str, ...]:
    metrics = tuple(part.strip() for part in text.split(",") if part.strip())
    if not metrics:
        raise SystemExit("Pareto metrics list cannot be empty.")
    invalid = [metric for metric in metrics if metric not in CORE_METRICS]
    if invalid:
        raise SystemExit(
            f"Unsupported Pareto metric(s): {', '.join(invalid)}. "
            f"Choose from: {', '.join(CORE_METRICS)}."
        )
    return metrics


def _default_pareto_metrics(metric: str, pareto_metrics_arg: str | None) -> tuple[str, ...]:
    if pareto_metrics_arg:
        return _parse_metric_list(pareto_metrics_arg)
    return ("latency", metric)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze DSE summary.csv and print top/pareto points")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("src/results/dse_runs/summary.csv"),
        help="Path to DSE summary CSV.",
    )
    parser.add_argument("--topk", type=int, default=10, help="Number of top rows to print.")
    parser.add_argument(
        "--metric",
        type=str,
        default="energy",
        choices=list(RANKING_METRICS),
        help="Metric to rank by and, by default, pair with latency for a 2D Pareto front.",
    )
    parser.add_argument(
        "--pareto-metrics",
        type=str,
        default=None,
        help="Optional comma-separated Pareto metrics, for example: latency,area,utilization.",
    )
    parser.add_argument(
        "--pareto-out",
        type=Path,
        default=None,
        help="Optional output CSV path for Pareto front. Defaults next to input CSV.",
    )
    args = parser.parse_args()

    rows = _load_rows(args.csv)
    ok = _ok_rows(rows)

    if not ok:
        raise SystemExit("No successful rows found in CSV (status=ok or returncode=0).")

    top_energy = _sorted_top(ok, args.metric, args.topk)
    top_latency = _sorted_top(ok, "latency", args.topk)

    _print_table(f"Top {len(top_energy)} by {args.metric}", top_energy)
    _print_table(f"Top {len(top_latency)} by latency", top_latency)

    pareto_metrics = _default_pareto_metrics(args.metric, args.pareto_metrics)

    pareto = _pareto_front(ok, pareto_metrics)

    if args.pareto_out is not None:
        pareto_out = args.pareto_out
    elif pareto_metrics == ("latency", args.metric):
        pareto_out = args.csv.with_name("pareto_latency_vs_" + args.metric + ".csv")
    else:
        pareto_out = args.csv.with_name("pareto_" + "_".join(pareto_metrics) + ".csv")

    for row in pareto:
        util = _utilization_percent(row)
        if util is not None:
            row["summary_utilization_percent"] = util

    fieldnames = sorted({k for row in pareto for k in row.keys()}) if pareto else []
    with pareto_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pareto)

    print(f"\nPareto points: {len(pareto)}")
    print(f"Pareto CSV: {pareto_out}")


if __name__ == "__main__":
    main()
