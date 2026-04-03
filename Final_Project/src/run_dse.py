from __future__ import annotations

import argparse
from pathlib import Path

from tltools.dse import run_dse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Timeloop+Accelergy memory-centric DSE sweep")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("src/dse/sweep.matmul.medium.yaml"),
        help="Path to DSE YAML config file.",
    )
    args = parser.parse_args()

    csv_path = run_dse(args.config)
    print(f"DSE finished. Summary CSV: {csv_path}")


if __name__ == "__main__":
    main()
