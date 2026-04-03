from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path

import matplotlib.pyplot as plt


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


def _extract_points(rows: list[dict[str, str]]) -> list[tuple[float, float, float, float, str]]:
    points: list[tuple[float, float, float, float, str]] = []
    for row in rows:
        latency = _metric(row, "latency")
        energy = _metric(row, "energy")
        area = _metric(row, "area")
        util = _metric(row, "utilization")
        run_name = str(row.get("run_name", ""))
        if None in (latency, energy, area, util):
            continue
        points.append((float(latency), float(energy), float(area), float(util), run_name))
    return points


def plot_pareto(
    pareto_csv: Path, out_png: Path, title: str | None = None, all_points_csv: Path | None = None
) -> None:
    pareto_rows = _load_rows(pareto_csv)
    pareto_points = _extract_points(pareto_rows)

    if not pareto_points:
        raise SystemExit(f"No plottable Pareto points in {pareto_csv}")

    # By default, overlay all points from sibling summary.csv when available.
    if all_points_csv is None:
        default_summary = pareto_csv.with_name("summary.csv")
        all_points_csv = default_summary if default_summary.exists() else pareto_csv

    all_rows = _load_rows(all_points_csv)
    all_points = _extract_points(all_rows)

    if not all_points:
        all_points = pareto_points

    p_lat = [p[0] for p in pareto_points]
    p_energy = [p[1] for p in pareto_points]
    p_area = [p[2] for p in pareto_points]
    p_util = [p[3] for p in pareto_points]
    p_labels = [p[4] for p in pareto_points]

    a_lat = [p[0] for p in all_points]
    a_energy = [p[1] for p in all_points]

    min_area, max_area = min(p_area), max(p_area)
    sizes = [_size_from_area(a, min_area, max_area) for a in p_area]

    fig, ax = plt.subplots(figsize=(9, 6))
    # Background: all design points.
    ax.scatter(a_lat, a_energy, s=22, c="lightgray", alpha=0.6, edgecolors="none", label="All points")

    # Foreground: Pareto points with utilization/area encoding.
    sc = ax.scatter(
        p_lat, p_energy, c=p_util, s=sizes, cmap="viridis", alpha=0.95, edgecolors="black", label="Pareto points"
    )
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Utilization (%)")

    # Draw projected Pareto curve in latency-energy plane.
    ordered = sorted(zip(p_lat, p_energy), key=lambda t: t[0])
    ax.plot([x for x, _ in ordered], [y for _, y in ordered], color="black", linewidth=1.6, alpha=0.9, label="Pareto curve")

    best_i = min(range(len(pareto_points)), key=lambda i: (p_lat[i], p_energy[i]))
    ax.annotate(
        p_labels[best_i],
        (p_lat[best_i], p_energy[best_i]),
        textcoords="offset points",
        xytext=(8, 8),
        fontsize=8,
    )

    ax.set_xlabel("Latency (cycles)")
    ax.set_ylabel("Energy (uJ)")
    ax.set_title(title or f"Pareto Front: {pareto_csv.stem}")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)

    # Legend for area size.
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Pareto CSV (latency vs energy; color=utilization; size=area).")
    parser.add_argument("--csv", type=Path, required=True, help="Input Pareto CSV path.")
    parser.add_argument(
        "--all-csv",
        type=Path,
        default=None,
        help="Optional CSV containing all points (defaults to sibling summary.csv).",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output PNG path.")
    parser.add_argument("--title", type=str, default=None, help="Optional plot title.")
    args = parser.parse_args()

    # Avoid ~/.matplotlib permission issues on some setups.
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

    out = args.out or args.csv.with_suffix(".png")
    plot_pareto(args.csv, out, args.title, args.all_csv)
    print(f"Saved plot: {out}")


if __name__ == "__main__":
    main()
