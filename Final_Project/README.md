# Final Project: Timeloop + Accelergy DSE Scaffold

This project now includes a clean, memory-centric DSE flow for systolic-array exploration.

## What was added

- `src/run_dse.py`: CLI entrypoint for design-space sweeps.
- `src/tltools/dse.py`: sweep engine (template rendering, run orchestration, CSV summary).
- `src/dse/sweep.matmul.medium.yaml`: medium matmul sweep configuration.
- `src/dse/templates/systolic_array_arch.template.yaml`: architecture template with placeholders.
- `src/dse/problem_example.yaml`, `src/dse/mapping_example.yaml`: starter workload + mapping.
- `src/tests/test_dse.py`: unit tests for DSE helpers.

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
python3 src/analyze_dse.py --csv src/results/dse_runs_light_matmul/summary.csv --true-pareto
python3 src/analyze_dse.py --csv src/results/dse_runs_medium_matmul/summary.csv --true-pareto
python3 src/analyze_dse.py --csv src/results/dse_runs_heavy_matmul/summary.csv --true-pareto

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



