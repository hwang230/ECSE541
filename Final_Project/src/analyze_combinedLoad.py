"""
plot_combined.py  –  Combined Pareto grid figures, one per simulator/dataflow.

Layout: rows = workloads (light, medium, heavy)
        cols = metric pairs (latency vs energy, latency vs area, latency vs utilization)

Usage examples
--------------
# Timeloop weight-stationary
python3 plot_combined.py \
    --tool timeloop_ws \
    --light  Final_Project/timeloop_ws_light_matmul_summary.csv \
    --medium Final_Project/timeloop_ws_medium_matmul_summary.csv \
    --heavy  Final_Project/timeloop_ws_heavy_matmul_summary.csv \
    --energy-metric energy \
    --out    Final_Project/combined_timeloop_ws.png

# SCALE-Sim output-stationary (no energy column → use latency/area/utilization only)
python3 plot_combined.py \
    --tool scalesim_os \
    --light  Final_Project/scalesim_os_light_matmul_summary.csv \
    --medium Final_Project/scalesim_os_medium_matmul_summary.csv \
    --out    Final_Project/combined_scalesim_os.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


# ── helpers (copied from analyze_dse.py) ─────────────────────────────────────

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


def _utilization_percent(row: dict[str, Any]) -> float | None:
    util = _to_float(row.get("summary_utilization_percent"))
    if util is None:
        throttle = _to_float(row.get("bandwidth_throttling_max"))
        if throttle is None:
            return None
        util = throttle * 100.0
    return max(0.0, min(100.0, util))


def _metric_value(row: dict[str, Any], metric: str) -> float | None:
    if metric == "latency":
        return (_to_float(row.get("summary_cycles"))
                or _to_float(row.get("cycles"))
                or _to_float(row.get("latency_ns")))
    if metric == "energy":
        return (_to_float(row.get("summary_energy_uj"))
                or _to_float(row.get("pj_per_compute")))
    if metric == "area":
        return (_to_float(row.get("area_proxy_um2"))
                or _to_float(row.get("summary_area_mm2"))
                or _to_float(row.get("area_um2_art_sum")))
    if metric == "utilization":
        return _utilization_percent(row)
    return _to_float(row.get(metric))


def _dominates(a: dict[str, Any], b: dict[str, Any], metrics: tuple[str, ...]) -> bool:
    dirs = {"latency": "min", "energy": "min", "area": "min", "utilization": "max"}
    a_vals = [_metric_value(a, m) for m in metrics]
    b_vals = [_metric_value(b, m) for m in metrics]
    if any(v is None for v in a_vals + b_vals):
        return False
    not_worse_all = True
    strictly_better_any = False
    for i, metric in enumerate(metrics):
        av, bv = float(a_vals[i]), float(b_vals[i])  # type: ignore[arg-type]
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
        if any(_metric_value(cand, m) is None for m in metrics):
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
    front.sort(key=lambda r: (
        _metric_value(r, metrics[0]) or float("inf"),
        _metric_value(r, metrics[1]) or float("inf"),
    ))
    return front


# ── axis labels ───────────────────────────────────────────────────────────────

AXIS_LABELS: dict[str, str] = {
    "latency":     "Latency (cycles)",
    "energy":      "Energy (uJ)",
    "area":        "Area Proxy (um²)",
    "utilization": "Utilization (%)",
}

WORKLOAD_LABELS = {"light": "Light", "medium": "Medium", "heavy": "Heavy"}


# ── main plotting function ────────────────────────────────────────────────────

def _plot_panel(
    ax: Any,
    rows: list[dict[str, Any]],
    x_metric: str,
    y_metric: str,
    col_title: str | None,
    row_label: str | None,
) -> None:
    """Draw one subplot panel: scatter of all points + Pareto curve."""
    plot_rows = [
        r for r in rows
        if _metric_value(r, x_metric) is not None
        and _metric_value(r, y_metric) is not None
        and _metric_value(r, "utilization") is not None
    ]

    if not plot_rows:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes,
                fontsize=9, color="grey")
        if col_title:
            ax.set_title(col_title, fontsize=9, fontweight="bold")
        if row_label:
            ax.set_ylabel(f"{row_label}\n{AXIS_LABELS[y_metric]}", fontsize=8)
        else:
            ax.set_ylabel(AXIS_LABELS[y_metric], fontsize=8)
        ax.set_xlabel(AXIS_LABELS[x_metric], fontsize=8)
        return

    pareto = _pareto_front(plot_rows, (x_metric, y_metric))

    x_all   = [float(_metric_value(r, x_metric) or 0) for r in plot_rows]
    y_all   = [float(_metric_value(r, y_metric) or 0) for r in plot_rows]
    util_all = [float(_metric_value(r, "utilization") or 0) for r in plot_rows]
    x_par   = [float(_metric_value(r, x_metric) or 0) for r in pareto]
    y_par   = [float(_metric_value(r, y_metric) or 0) for r in pareto]

    sc = ax.scatter(x_all, y_all, c=util_all, cmap="viridis",
                    s=28, edgecolors="white", linewidths=0.3, alpha=0.9, vmin=0, vmax=100)

    if pareto:
        ax.scatter(x_par, y_par, s=48, facecolors="none",
                   edgecolors="crimson", linewidths=0.9, zorder=4, label="Pareto pts")
        ax.plot(x_par, y_par, color="crimson", linewidth=1.2, alpha=0.85,
                zorder=5, label="Pareto front")

        # Annotate each Pareto point with its key config parameters
        texts = []
        for r, xv, yv in zip(pareto, x_par, y_par):
            pe_x = r.get("pe_x") or r.get("array_rows") or "?"
            pe_y = r.get("pe_y") or r.get("array_cols") or "?"
            bw   = r.get("backing_storage_bw") or r.get("dram_bw") or "?"
            gb_depth = _to_float(r.get("global_buffer_depth"))
            gb_mb = f"{int(gb_depth) // (1024*1024)}MB" if gb_depth else "?"
            label = f"{pe_x}×{pe_y}\n{bw}GB/s\n{gb_mb}"
            txt = ax.annotate(
                label,
                xy=(xv, yv),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=5,
                color="crimson",
                zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.6),
            )
            texts.append(txt)

        # Attempt to adjust labels to avoid overlap if adjustText is available
        try:
            from adjustText import adjust_text
            adjust_text(texts, ax=ax, only_move={"points": "y", "texts": "xy"},
                        arrowprops=dict(arrowstyle="-", color="crimson", lw=0.4))
        except ImportError:
            pass

    if col_title:
        ax.set_title(col_title, fontsize=9, fontweight="bold")
    if row_label:
        ax.set_ylabel(f"{row_label}\n{AXIS_LABELS[y_metric]}", fontsize=8)
    else:
        ax.set_ylabel(AXIS_LABELS[y_metric], fontsize=8)
    ax.set_xlabel(AXIS_LABELS[x_metric], fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.2)

    return sc  # type: ignore[return-value]


def build_combined_figure(
    workload_csvs: dict[str, Path],   # e.g. {"light": Path(...), "medium": ..., "heavy": ...}
    tool_label: str,
    out_path: Path,
    plot_specs: list[tuple[str, str]],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    workload_keys = [k for k in ("light", "medium", "heavy") if k in workload_csvs]
    n_rows = len(workload_keys)
    n_cols = len(plot_specs)

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(4.5 * n_cols, 3.8 * n_rows),
        dpi=180,
        squeeze=False,
    )
    fig.suptitle(f"DSE Pareto Analysis — {tool_label}", fontsize=13, fontweight="bold", y=1.01)

    last_sc = None
    for row_idx, wl_key in enumerate(workload_keys):
        rows = _ok_rows(_load_rows(workload_csvs[wl_key]))
        row_label = WORKLOAD_LABELS[wl_key]

        for col_idx, (x_metric, y_metric) in enumerate(plot_specs):
            ax = axes[row_idx][col_idx]
            col_title = f"{x_metric} vs {y_metric}" if row_idx == 0 else None
            sc = _plot_panel(ax, rows, x_metric, y_metric, col_title, row_label if col_idx == 0 else None)
            if sc is not None:
                last_sc = sc

    # shared colorbar on the right
    if last_sc is not None:
        cbar_ax = fig.add_axes([1.01, 0.15, 0.02, 0.7])
        cbar = fig.colorbar(last_sc, cax=cbar_ax)
        cbar.set_label("PE Utilization (%)", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a combined Pareto grid figure (workloads × metric pairs) for one tool."
    )
    parser.add_argument("--tool", required=True,
                        help="Tool/dataflow label for the figure title, e.g. 'Timeloop WS'.")
    parser.add_argument("--light",  type=Path, default=None, help="CSV for light workload.")
    parser.add_argument("--medium", type=Path, default=None, help="CSV for medium workload.")
    parser.add_argument("--heavy",  type=Path, default=None, help="CSV for heavy workload.")
    parser.add_argument("--out",    type=Path, required=True, help="Output PNG path.")
    parser.add_argument(
        "--energy-metric", action="store_true",
        help="Include latency-vs-energy column (requires energy data, e.g. Timeloop+Accelergy).",
    )
    args = parser.parse_args()

    workload_csvs: dict[str, Path] = {}
    for key, val in [("light", args.light), ("medium", args.medium), ("heavy", args.heavy)]:
        if val is not None:
            workload_csvs[key] = val

    if not workload_csvs:
        raise SystemExit("Provide at least one of --light / --medium / --heavy.")

    # columns: always latency/area and latency/utilization; add latency/energy if requested
    plot_specs: list[tuple[str, str]] = [("latency", "area"), ("latency", "utilization")]
    if args.energy_metric:
        plot_specs.insert(0, ("latency", "energy"))

    build_combined_figure(workload_csvs, args.tool, args.out, plot_specs)


if __name__ == "__main__":
    main()