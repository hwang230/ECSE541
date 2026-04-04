# Final Project: Timeloop + Accelergy DSE Scaffold

This project now includes a clean, memory-centric DSE flow for systolic-array exploration.

## What was added

- `src/run_dse.py`: CLI entrypoint for design-space sweeps.
- `src/tltools/dse.py`: sweep engine (template rendering, run orchestration, CSV summary).
- `src/dse/sweep.matmul.medium.yaml`: medium matmul sweep configuration.
- `src/dse/templates/systolic_array_arch.template.yaml`: architecture template with placeholders.
- `src/dse/problem_example.yaml`, `src/dse/mapping_example.yaml`: starter workload + mapping.

## Setup

Run everything from the project root:

```bash
cd ./ECSE541/Final_Project
```

Make sure `accelergy`, `timeloop-model`, and `timeloop-mapper` are available on `PATH`.

If you are using the local Timeloop Python environment in this repo, a typical setup is:

```bash
source timeloop-python/venv/bin/activate
export PATH="$PWD/timeloop/build:$PWD/timeloop/build/applications/model:$PWD/timeloop/build/applications/mapper:$PATH"
export PATH="$PWD/timeloop-python/venv/bin:$PATH"
```

Verify the tools before running DSE:

```bash
which timeloop-model
which timeloop-mapper
which accelergy
```

For Scale-Sim support, install it into the same local venv:

```bash
timeloop-python/venv/bin/pip install scalesim
```

You can verify the install with:

```bash
timeloop-python/venv/bin/python -m scalesim.scale --help
```

## Quick Start

Run the default medium-workload DSE:

```bash
python3 src/run_dse.py --config src/dse/sweep.matmul.medium.yaml
```

Results are saved to:

- `src/results/dse_runs_medium_matmul/<design-point>/...` (per-point artifacts)
- `src/results/dse_runs_medium_matmul/summary.csv` (aggregated metrics)

## Active Sweep Knobs (`sweep.matmul.medium.yaml`)

Only parameters with more than one candidate value live under `sweep:`:

- `pe_dim`: square PE array dimension, expanded internally to `pe_x = pe_y`
- `global_buffer_depth`: backing storage capacity
- `backing_storage_bw`: backing storage read/write bandwidth


## Run DSE And Pareto

Run any workload sweep with:

```bash
python3 src/run_dse.py --config src/dse/sweep.matmul.light.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.medium.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.heavy.yaml
```

Then generate the Pareto front from the corresponding `summary.csv`:

```bash
python3 src/analyze_dse.py --csv src/results/dse_runs_light_matmul/summary.csv --pareto-metrics latency,energy,area,utilization
python3 src/analyze_dse.py --csv src/results/dse_runs_medium_matmul/summary.csv --pareto-metrics latency,energy,area,utilization
python3 src/analyze_dse.py --csv src/results/dse_runs_heavy_matmul/summary.csv --pareto-metrics latency,energy,area,utilization

```

If you want a PNG plot of the Pareto front:

```bash
python3 src/plot_pareto.py \
  --csv src/results/dse_runs_light_matmul/pareto_true_latency_energy_area_util.csv \
  --all-csv src/results/dse_runs_light_matmul/summary.csv

python3 src/plot_pareto.py \
  --csv src/results/dse_runs_medium_matmul/pareto_true_latency_energy_area_util.csv \
  --all-csv src/results/dse_runs_medium_matmul/summary.csv

python3 src/plot_pareto.py \
  --csv src/results/dse_runs_heavy_matmul/pareto_true_latency_energy_area_util.csv \
  --all-csv src/results/dse_runs_heavy_matmul/summary.csv

```

## Run Scale-Sim

Use the new helper to run a single GEMM workload through Scale-Sim from this repo:

```bash
python3 src/run_scalesim.py \
  --run-dir src/results/scalesim_demo \
  --m 64 --n 64 --k 64 \
  --array-rows 16 --array-cols 16 \
  --ifmap-sram-kb 64 \
  --filter-sram-kb 64 \
  --ofmap-sram-kb 64 \
  --bandwidths 16,16,16
```

This generates:

- `src/results/scalesim_demo/scalesim.cfg`
- `src/results/scalesim_demo/scalesim_topology.csv`
- `src/results/scalesim_demo/scalesim_layout.csv`
- `src/results/scalesim_demo/scalesim_out/scalesim_run/COMPUTE_REPORT.csv`
- `src/results/scalesim_demo/scalesim_out/scalesim_run/BANDWIDTH_REPORT.csv`
- `src/results/scalesim_demo/scalesim_out/scalesim_run/DETAILED_ACCESS_REPORT.csv`

The helper also prints parsed metrics such as:

- total cycles
- total cycles including prefetch
- stall cycles
- overall utilization
- mapping efficiency
- average SRAM/DRAM bandwidths

## Run Scale-Sim DSE

The DSE driver now supports a Scale-Sim backend selected in config with `simulator: scalesim`.

Example workload sweeps:

```bash
python3 src/run_dse.py --config src/dse/sweep.matmul.light.scalesim.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.medium.scalesim.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.heavy.scalesim.yaml
```

These write workload-specific summary CSVs such as:

- `src/results/scalesim_runs_light_matmul/summary.csv`
- `src/results/scalesim_runs_medium_matmul/summary.csv`
- `src/results/scalesim_runs_heavy_matmul/summary.csv`

Scale-Sim results do not include Accelergy energy, so the recommended Pareto flow is a 3D front over latency, area, and utilization:

```bash
python3 src/analyze_dse.py \
  --csv src/results/scalesim_runs_light_matmul/summary.csv \
  --pareto-metrics latency,area,utilization

python3 src/analyze_dse.py \
  --csv src/results/scalesim_runs_medium_matmul/summary.csv \
  --pareto-metrics latency,area,utilization

python3 src/analyze_dse.py \
  --csv src/results/scalesim_runs_heavy_matmul/summary.csv \
  --pareto-metrics latency,area,utilization
```

This produces Pareto CSVs such as:

- `src/results/scalesim_runs_light_matmul/pareto_latency_area_utilization.csv`
- `src/results/scalesim_runs_medium_matmul/pareto_latency_area_utilization.csv`
- `src/results/scalesim_runs_heavy_matmul/pareto_latency_area_utilization.csv`

You can also generate a Scale-Sim Pareto plot directly. A good default view is latency on the x-axis, area on the y-axis, and utilization as color:

```bash
python3 src/plot_pareto.py \
  --csv src/results/scalesim_runs_light_matmul/pareto_latency_area_utilization.csv \
  --all-csv src/results/scalesim_runs_light_matmul/summary.csv \
  --y-metric area \
  --out src/results/scalesim_runs_light_matmul/pareto_latency_area_utilization.png

python3 src/plot_pareto.py \
  --csv src/results/scalesim_runs_medium_matmul/pareto_latency_area_utilization.csv \
  --all-csv src/results/scalesim_runs_medium_matmul/summary.csv \
  --y-metric area \
  --out src/results/scalesim_runs_medium_matmul/pareto_latency_area_utilization.png

python3 src/plot_pareto.py \
  --csv src/results/scalesim_runs_heavy_matmul/pareto_latency_area_utilization.csv \
  --all-csv src/results/scalesim_runs_heavy_matmul/summary.csv \
  --y-metric area \
  --out src/results/scalesim_runs_heavy_matmul/pareto_latency_area_utilization.png
```

This produces:

- `src/results/scalesim_runs_light_matmul/pareto_latency_area_utilization.png`
- `src/results/scalesim_runs_medium_matmul/pareto_latency_area_utilization.png`
- `src/results/scalesim_runs_heavy_matmul/pareto_latency_area_utilization.png`
