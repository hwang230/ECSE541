# Final Project: Timeloop and SCALE-Sim DSE

This repo supports systolic-array design-space exploration with two simulators:

- Timeloop + Accelergy
- SCALE-Sim

## Core Files

- `src/run_dse.py`: runs sweep configs
- `src/run_scalesim.py`: runs a single direct SCALE-Sim experiment
- `src/analyze_dse.py`: generates Pareto CSVs and plots
- `src/tltools/dse.py`: shared DSE engine

## Setup

Run from the project root:

```bash
cd ./ECSE541/Final_Project
```

Activate the local environment and expose Timeloop binaries:

```bash
source timeloop-python/venv/bin/activate
export PATH="$PWD/timeloop/build:$PWD/timeloop/build/applications/model:$PWD/timeloop/build/applications/mapper:$PWD/timeloop-python/venv/bin:$PATH"
```

Verify:

```bash
which timeloop-model
which timeloop-mapper
which accelergy
```

Install SCALE-Sim if needed:

```bash
timeloop-python/venv/bin/pip install scalesim
```

## Experiment Matrix

Timeloop output-stationary:

- `src/dse/sweep.matmul.light.yaml`
- `src/dse/sweep.matmul.medium.yaml`
- `src/dse/sweep.matmul.heavy.yaml`

Timeloop weight-stationary:

- `src/dse/sweep.matmul.light.ws.yaml`
- `src/dse/sweep.matmul.medium.ws.yaml`
- `src/dse/sweep.matmul.heavy.ws.yaml`

SCALE-Sim weight-stationary:

- `src/dse/sweep.matmul.light.scalesim.yaml`
- `src/dse/sweep.matmul.medium.scalesim.yaml`
- `src/dse/sweep.matmul.heavy.scalesim.yaml`

SCALE-Sim output-stationary:

- `src/dse/sweep.matmul.light.os.scalesim.yaml`
- `src/dse/sweep.matmul.medium.os.scalesim.yaml`

Supporting inputs:

- `src/dse/problem_example.yaml`
- `src/dse/mapping_example.yaml`
- `src/dse/mapping_weight_stationary.yaml`
- `src/dse/templates/systolic_array_arch.template.yaml`

## Run Sweeps

Timeloop OS:

```bash
python3 src/run_dse.py --config src/dse/sweep.matmul.light.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.medium.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.heavy.yaml
```

Timeloop WS:

```bash
python3 src/run_dse.py --config src/dse/sweep.matmul.light.ws.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.medium.ws.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.heavy.ws.yaml
```

SCALE-Sim WS:

```bash
python3 src/run_dse.py --config src/dse/sweep.matmul.light.scalesim.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.medium.scalesim.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.heavy.scalesim.yaml
```

SCALE-Sim OS:

```bash
python3 src/run_dse.py --config src/dse/sweep.matmul.light.os.scalesim.yaml
python3 src/run_dse.py --config src/dse/sweep.matmul.medium.os.scalesim.yaml
```

Sweep knobs used across the configs:

- `pe_dim`
- `global_buffer_depth`
- `backing_storage_bw`

## Analyze Results

Timeloop Pareto CSV:

```bash
python3 src/analyze_dse.py --csv src/results/dse_runs_light_matmul/summary.csv --pareto-metrics latency,energy,area,utilization
```

Timeloop pair plots:

```bash
python3 src/analyze_dse.py --csv src/results/dse_runs_light_matmul/summary.csv --pareto-metrics latency,energy,area,utilization --plot-pairs --workload-label "Light" --tool-label "Timeloop"
python3 src/analyze_dse.py --csv src/results/dse_runs_light_matmul_ws/summary.csv --pareto-metrics latency,energy,area,utilization --plot-pairs --workload-label "Light" --tool-label "Timeloop"
```

SCALE-Sim Pareto CSV and overlay plots:

```bash
python3 src/analyze_dse.py --csv src/results/scalesim_runs_light_matmul/summary.csv --pareto-metrics latency,area,utilization --plot-overlay --workload-label "Light" --tool-label "SCALE-Sim"
python3 src/analyze_dse.py --csv src/results/scalesim_runs_medium_matmul/summary.csv --pareto-metrics latency,area,utilization --plot-overlay --workload-label "Medium" --tool-label "SCALE-Sim"
```

Typical outputs:

- `summary.csv`
- `pareto_*.csv`
- `pair_*.png` for Timeloop
- `highlighted_latency_vs_area.png` and `highlighted_latency_vs_utilization.png` for SCALE-Sim

## Notes

- Timeloop results are maintained for both output-stationary and weight-stationary mappings.
- SCALE-Sim results are maintained for weight-stationary on light, medium, and heavy workloads.
- SCALE-Sim output-stationary is kept for light and medium workloads.
- Heavy SCALE-Sim output-stationary was dropped because it was not practical to complete within runtime limits.
