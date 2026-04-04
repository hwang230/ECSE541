from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path

import matplotlib.pyplot as plt

Y_AXIS_LABELS = {
    "latency": "Latency (cycles)",
    "energy": "Energy (uJ)",
    "utilization": "Utilization (%)",
    "area": "Area Proxy (um^2)",
}


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


def _utilization_percent(row: dict[str, str]) -> float | None:
    util = _to_float(row.get("summary_utilization_percent"))
    if util is None:
        throttle = _to_float(row.get("bandwidth_throttling_max"))
        if throttle is None:
            return None
        util = throttle * 100.0
    return max(0.0, min(100.0, util))


def _metric(row: dict[str, str], name: str) -> float | None:
    if name == "latency":
        return _to_float(row.get("summary_cycles")) or _to_float(row.get("cycles")) or _to_float(
            row.get("latency_ns")
        )
    if name == "energy":
        return _to_float(row.get("summary_energy_uj")) or _to_float(row.get("pj_per_compute"))
    if name == "area":
        return (
            _to_float(row.get("area_proxy_um2"))
            or _to_float(row.get("summary_area_mm2"))
            or _to_float(row.get("area_um2_art_sum"))
        )
    if name == "utilization":
        return _utilization_percent(row)
    return _to_float(row.get(name))


def _load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _size_from_area(area: float, min_area: float, max_area: float) -> float:
    if math.isclose(min_area, max_area):
        return 80.0
    norm = (area - min_area) / (max_area - min_area)
    return 40.0 + 200.0 * norm


def _extract_points(
    rows: list[dict[str, str]], y_metric: str
) -> list[tuple[float, float, float, float, str]]:
    points: list[tuple[float, float, float, float, str]] = []
    for row in rows:
        latency = _metric(row, "latency")
        y_value = _metric(row, y_metric)
        area = _metric(row, "area")
        util = _metric(row, "utilization")
        run_name = str(row.get("run_name", ""))
        if None in (latency, y_value, area, util):
            continue
        points.append((float(latency), float(y_value), float(area), float(util), run_name))
    return points


def _extract_metric_points(
    rows: list[dict[str, str]], x_metric: str, y_metric: str
) -> list[tuple[float, float, str]]:
    points: list[tuple[float, float, str]] = []
    for row in rows:
        x_value = _metric(row, x_metric)
        y_value = _metric(row, y_metric)
        if None in (x_value, y_value):
            continue
        points.append((float(x_value), float(y_value), str(row.get("run_name", ""))))
    return points


def plot_pareto(
    pareto_csv: Path,
    out_png: Path,
    title: str | None = None,
    all_points_csv: Path | None = None,
    y_metric: str = "energy",
) -> None:
    pareto_rows = _load_rows(pareto_csv)
    pareto_points = _extract_points(pareto_rows, y_metric=y_metric)

    if not pareto_points:
        raise SystemExit(f"No plottable Pareto points in {pareto_csv}")

    if all_points_csv is None:
        summary_csv = pareto_csv.with_name("summary.csv")
        all_points_csv = summary_csv if summary_csv.exists() else pareto_csv

    all_points = _extract_points(_load_rows(all_points_csv), y_metric=y_metric)

    if not all_points:
        all_points = pareto_points

    p_lat, p_y, p_area, p_util, p_labels = map(list, zip(*pareto_points))
    a_lat, a_y, *_ = map(list, zip(*all_points))

    min_area, max_area = min(p_area), max(p_area)
    sizes = [_size_from_area(a, min_area, max_area) for a in p_area]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(a_lat, a_y, s=22, c="lightgray", alpha=0.6, edgecolors="none", label="All points")

    sc = ax.scatter(
        p_lat,
        p_y,
        c=p_util,
        s=sizes,
        cmap="viridis",
        vmin=0.0,
        vmax=100.0,
        alpha=0.95,
        edgecolors="black",
        label="Pareto points",
    )
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Utilization (%)")

    curve_points = sorted(zip(p_lat, p_y), key=lambda point: point[0])
    ax.plot(
        [x for x, _ in curve_points],
        [y for _, y in curve_points],
        color="black",
        linewidth=1.6,
        alpha=0.9,
        label="Pareto curve",
    )

    best_i = min(range(len(pareto_points)), key=lambda i: (p_lat[i], p_y[i]))
    ax.annotate(
        p_labels[best_i],
        (p_lat[best_i], p_y[best_i]),
        textcoords="offset points",
        xytext=(8, 8),
        fontsize=8,
    )

    ax.set_xlabel("Latency (cycles)")
    ax.set_ylabel(Y_AXIS_LABELS.get(y_metric, y_metric))
    ax.set_title(title or f"Pareto Front: {pareto_csv.stem}")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)

    if not math.isclose(min_area, max_area):
        for frac, label in [(0.0, "small area"), (0.5, "medium area"), (1.0, "large area")]:
            area_val = min_area + frac * (max_area - min_area)
            ax.scatter([], [], s=_size_from_area(area_val, min_area, max_area), c="gray", alpha=0.5, label=label)
        ax.legend(title="Marker size ~ area", loc="best")
    else:
        ax.legend(loc="best")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def plot_metric_pair(
    csv_path: Path,
    out_png: Path,
    *,
    x_metric: str,
    y_metric: str,
    title: str | None = None,
) -> None:
    points = _extract_metric_points(_load_rows(csv_path), x_metric=x_metric, y_metric=y_metric)
    if not points:
        raise SystemExit(f"No plottable points in {csv_path} for {x_metric} vs {y_metric}")

    x_vals, y_vals, labels = map(list, zip(*points))
    best_i = min(range(len(points)), key=lambda i: (x_vals[i], y_vals[i]))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(x_vals, y_vals, s=42, c="#2f7f7f", alpha=0.85, edgecolors="black", linewidths=0.4)
    ax.annotate(
        labels[best_i],
        (x_vals[best_i], y_vals[best_i]),
        textcoords="offset points",
        xytext=(8, 8),
        fontsize=8,
    )
    ax.set_xlabel(Y_AXIS_LABELS.get(x_metric, x_metric))
    ax.set_ylabel(Y_AXIS_LABELS.get(y_metric, y_metric))
    ax.set_title(title or f"{x_metric} vs {y_metric}")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot Pareto fronts or plain pairwise metric scatter plots."
    )
    parser.add_argument("--csv", type=Path, required=True, help="Input CSV path.")
    parser.add_argument(
        "--all-csv",
        type=Path,
        default=None,
        help="Optional CSV containing all points (defaults to sibling summary.csv).",
    )
    parser.add_argument(
        "--y-metric",
        type=str,
        default="energy",
        choices=["latency", "energy", "utilization", "area"],
        help="Metric to use on the y-axis.",
    )
    parser.add_argument(
        "--x-metric",
        type=str,
        default=None,
        choices=["latency", "energy", "utilization", "area"],
        help="If set, make a plain 2-metric scatter plot instead of a Pareto plot.",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output PNG path.")
    parser.add_argument("--title", type=str, default=None, help="Optional plot title.")
    args = parser.parse_args()

    # Avoid ~/.matplotlib permission issues on some setups.
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

    out = args.out or args.csv.with_suffix(".png")
    if args.x_metric is None:
        plot_pareto(args.csv, out, args.title, args.all_csv, args.y_metric)
    else:
        plot_metric_pair(args.csv, out, x_metric=args.x_metric, y_metric=args.y_metric, title=args.title)
    print(f"Saved plot: {out}")


if __name__ == "__main__":
    main()
