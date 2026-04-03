from __future__ import annotations

import argparse
from pathlib import Path
from pprint import pprint

from tltools.runner import timeloop_model_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Timeloop model and print parsed metrics.")
    parser.add_argument("--run-dir", type=Path, default=Path("src/tests/fixtures/minimal"))
    parser.add_argument("--arch", default="arch_example.yaml")
    parser.add_argument("--problem", default="problem_example.yaml")
    parser.add_argument("--mapping", default="mapping_example.yaml")
    parser.add_argument("--clock-seconds", type=float, default=1e-9)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    result = timeloop_model_metrics(
        args.arch,
        args.problem,
        args.mapping,
        cwd=args.run_dir,
        clock_seconds=args.clock_seconds,
        timeout=args.timeout,
    )

    pprint(result["metrics"])
    print("ERT summary present:", result["outputs"]["ert_summary"] is not None)
    print("ART summary present:", result["outputs"]["art_summary"] is not None)


if __name__ == "__main__":
    main()
