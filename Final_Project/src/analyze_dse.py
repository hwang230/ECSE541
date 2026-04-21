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


def _plot_title_suffix(csv_path: Path, workload_label: str | None, tool_label: str | None) -> str:
    parts: list[str] = []
    if workload_label:
        parts.append(workload_label)
    if tool_label:
        parts.append(tool_label)
    if not parts:
        parts.append(csv_path.parent.name)
    return ", ".join(parts)


def _import_matplotlib() -> tuple[Any, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return matplotlib, plt


def _write_overlay_plots(
    *,
    rows: list[dict[str, Any]],
    pareto_rows: list[dict[str, Any]],
    csv_path: Path,
    workload_label: str | None,
    tool_label: str | None,
    output_prefix: str = "",
) -> list[Path]:
    _, plt = _import_matplotlib()

    all_points = [
        row
        for row in rows
        if _metric_value(row, "latency") is not None
        and _metric_value(row, "area") is not None
        and _metric_value(row, "utilization") is not None
    ]
    pareto_points = [
        row
        for row in pareto_rows
        if _metric_value(row, "latency") is not None
        and _metric_value(row, "area") is not None
        and _metric_value(row, "utilization") is not None
    ]

    all_points.sort(
        key=lambda row: (
            float(_metric_value(row, "latency") or 0.0),
            float(_metric_value(row, "area") or 0.0),
            -(float(_metric_value(row, "utilization") or 0.0)),
            str(row.get("run_name", "")),
        )
    )
    pareto_points.sort(
        key=lambda row: (
            float(_metric_value(row, "latency") or 0.0),
            float(_metric_value(row, "area") or 0.0),
            -(float(_metric_value(row, "utilization") or 0.0)),
            str(row.get("run_name", "")),
        )
    )

    title_suffix = _plot_title_suffix(csv_path, workload_label, tool_label)
    prefix = f"{output_prefix}_" if output_prefix else ""
    out_area = csv_path.with_name(f"{prefix}highlighted_latency_vs_area.png")
    out_util = csv_path.with_name(f"{prefix}highlighted_latency_vs_utilization.png")

    all_latency = [float(_metric_value(row, "latency") or 0.0) for row in all_points]
    all_area = [float(_metric_value(row, "area") or 0.0) for row in all_points]
    all_util = [float(_metric_value(row, "utilization") or 0.0) for row in all_points]
    pareto_latency = [float(_metric_value(row, "latency") or 0.0) for row in pareto_points]
    pareto_area = [float(_metric_value(row, "area") or 0.0) for row in pareto_points]
    pareto_util = [float(_metric_value(row, "utilization") or 0.0) for row in pareto_points]

    fig, ax = plt.subplots(figsize=(8.4, 5.4), dpi=180)
    scatter = ax.scatter(
        all_latency,
        all_area,
        c=all_util,
        cmap="viridis",
        s=46,
        edgecolors="white",
        linewidths=0.45,
        alpha=0.95,
    )
    if pareto_points:
        ax.plot(
            pareto_latency,
            pareto_area,
            color="black",
            linewidth=1.5,
            alpha=0.9,
            zorder=4,
            label="Pareto",
        )
        ax.legend(frameon=False, loc="best")
    ax.set_title(f"Latency vs Area ({title_suffix})")
    ax.set_xlabel("Latency (cycles)")
    ax.set_ylabel("Area Proxy (um^2)")
    ax.grid(True, alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Utilization (%)")
    fig.tight_layout()
    fig.savefig(out_area, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=180)
    ax.scatter(
        all_latency,
        all_util,
        s=28,
        color="#d8decf",
        edgecolors="none",
        alpha=0.95,
        label=f"All Points ({title_suffix})",
    )
    if pareto_points:
        ax.plot(
            pareto_latency,
            pareto_util,
            color="black",
            linewidth=1.5,
            alpha=0.9,
            zorder=4,
            label="Pareto",
        )
    ax.set_title(f"Latency vs Utilization ({title_suffix})")
    ax.set_xlabel("Latency (cycles)")
    ax.set_ylabel("Utilization (%)")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(out_util, bbox_inches="tight")
    plt.close(fig)

    return [out_area, out_util]


def _pair_plot_filename(x_metric: str, y_metric: str) -> str:
    return f"pair_{x_metric}_vs_{y_metric}.png"


def _metric_axis_label(metric: str) -> str:
    labels = {
        "latency": "Latency (cycles)",
        "energy": "Energy (uJ)",
        "area": "Area Proxy (um^2)",
        "utilization": "Utilization (%)",
    }
    return labels[metric]


def _metric_plot_title(metric: str) -> str:
    titles = {
        "latency": "latency",
        "energy": "energy",
        "area": "area",
        "utilization": "utilization",
    }
    return titles[metric]


def _write_pair_pareto_plots(
    *,
    rows: list[dict[str, Any]],
    csv_path: Path,
    workload_label: str | None,
    tool_label: str | None,
    output_prefix: str = "",
) -> list[Path]:
    _, plt = _import_matplotlib()

    plot_specs = [
        ("latency", "energy"),
        ("latency", "area"),
        ("area", "energy"),
    ]
    title_suffix = _plot_title_suffix(csv_path, workload_label, tool_label)
    written: list[Path] = []

    for x_metric, y_metric in plot_specs:
        plot_rows = [
            row
            for row in rows
            if _metric_value(row, x_metric) is not None
            and _metric_value(row, y_metric) is not None
            and _metric_value(row, "utilization") is not None
        ]
        plot_rows.sort(
            key=lambda row: (
                float(_metric_value(row, x_metric) or 0.0),
                float(_metric_value(row, y_metric) or 0.0),
                -(float(_metric_value(row, "utilization") or 0.0)),
                str(row.get("run_name", "")),
            )
        )

        pareto_rows = _pareto_front(plot_rows, (x_metric, y_metric))
        x_all = [float(_metric_value(row, x_metric) or 0.0) for row in plot_rows]
        y_all = [float(_metric_value(row, y_metric) or 0.0) for row in plot_rows]
        util_all = [float(_metric_value(row, "utilization") or 0.0) for row in plot_rows]
        x_pareto = [float(_metric_value(row, x_metric) or 0.0) for row in pareto_rows]
        y_pareto = [float(_metric_value(row, y_metric) or 0.0) for row in pareto_rows]

        prefix = f"{output_prefix}_" if output_prefix else ""
        out_path = csv_path.with_name(f"{prefix}{_pair_plot_filename(x_metric, y_metric)}")
        fig, ax = plt.subplots(figsize=(9, 6), dpi=180)

        scatter = ax.scatter(
            x_all,
            y_all,
            c=util_all,
            cmap="viridis",
            s=52,
            edgecolors="white",
            linewidths=0.45,
            alpha=0.95,
            label="All points",
        )
        if pareto_rows:
            ax.scatter(
                x_pareto,
                y_pareto,
                s=68,
                facecolors="none",
                edgecolors="black",
                linewidths=1.0,
                zorder=4,
                label="Pareto points",
            )
            ax.plot(
                x_pareto,
                y_pareto,
                color="black",
                linewidth=1.5,
                alpha=0.9,
                zorder=5,
                label="Pareto curve",
            )

        ax.set_title(
            f"{title_suffix}: {_metric_plot_title(x_metric)} vs {_metric_plot_title(y_metric)}"
        )
        ax.set_xlabel(_metric_axis_label(x_metric))
        ax.set_ylabel(_metric_axis_label(y_metric))
        ax.grid(True, alpha=0.25)
        cbar = fig.colorbar(scatter, ax=ax)
        cbar.set_label("Utilization (%)")
        ax.legend(frameon=False, loc="best")
        fig.tight_layout()
        fig.savefig(out_path, bbox_inches="tight")
        plt.close(fig)
        written.append(out_path)

    return written


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
    parser.add_argument(
        "--plot-overlay",
        action="store_true",
        help="Write overlay plots that show all points and a Pareto curve.",
    )
    parser.add_argument(
        "--plot-pairs",
        action="store_true",
        help="Write pair plots with utilization-colored points and pairwise Pareto fronts.",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="",
        help="Optional prefix for all output filenames to avoid overwriting (e.g. 'timeloop_ws_medium').",
    )
    parser.add_argument(
        "--workload-label",
        type=str,
        default=None,
        help="Optional workload label to include in plot titles.",
    )
    parser.add_argument(
        "--tool-label",
        type=str,
        default=None,
        help="Optional simulator/tool label to include in plot titles.",
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

    prefix = f"{args.output_prefix}_" if args.output_prefix else ""
    if args.pareto_out is not None:
        pareto_out = args.pareto_out
    elif pareto_metrics == ("latency", args.metric):
        pareto_out = args.csv.with_name(f"{prefix}pareto_latency_vs_{args.metric}.csv")
    else:
        pareto_out = args.csv.with_name(f"{prefix}pareto_{'_'.join(pareto_metrics)}.csv")

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

    if args.plot_overlay:
        plot_paths = _write_overlay_plots(
            rows=ok,
            pareto_rows=pareto,
            csv_path=args.csv,
            workload_label=args.workload_label,
            tool_label=args.tool_label,
            output_prefix=args.output_prefix,
        )
        for path in plot_paths:
            print(f"Plot: {path}")

    if args.plot_pairs:
        plot_paths = _write_pair_pareto_plots(
            rows=ok,
            csv_path=args.csv,
            workload_label=args.workload_label,
            tool_label=args.tool_label,
            output_prefix=args.output_prefix,
        )
        for path in plot_paths:
            print(f"Plot: {path}")


if __name__ == "__main__":
    main()