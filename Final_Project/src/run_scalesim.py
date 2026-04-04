from __future__ import annotations

import argparse
from pathlib import Path
from pprint import pprint

from tltools.scalesim_runner import run_scalesim_gemm


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single GEMM workload in Scale-Sim.")
    parser.add_argument("--run-dir", type=Path, default=Path("src/results/scalesim_demo"))
    parser.add_argument("--m", type=int, default=512)
    parser.add_argument("--n", type=int, default=512)
    parser.add_argument("--k", type=int, default=256)
    parser.add_argument("--array-rows", type=int, default=32)
    parser.add_argument("--array-cols", type=int, default=32)
    parser.add_argument("--ifmap-sram-kb", type=int, default=256)
    parser.add_argument("--filter-sram-kb", type=int, default=256)
    parser.add_argument("--ofmap-sram-kb", type=int, default=256)
    parser.add_argument("--dataflow", default="ws", choices=["ws", "os", "is"])
    parser.add_argument(
        "--bandwidths",
        default="16,16,16",
        help="Comma-separated IFMAP,FILTER,OFMAP DRAM bandwidths in words/cycle.",
    )
    parser.add_argument("--clock-seconds", type=float, default=1e-9)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    bandwidths = tuple(int(x.strip()) for x in args.bandwidths.split(","))
    if len(bandwidths) != 3:
        raise SystemExit("--bandwidths must contain exactly 3 comma-separated integers.")

    result = run_scalesim_gemm(
        run_dir=args.run_dir,
        m=args.m,
        n=args.n,
        k=args.k,
        array_rows=args.array_rows,
        array_cols=args.array_cols,
        ifmap_sram_kb=args.ifmap_sram_kb,
        filter_sram_kb=args.filter_sram_kb,
        ofmap_sram_kb=args.ofmap_sram_kb,
        dataflow=args.dataflow,
        bandwidths=bandwidths,
        clock_seconds=args.clock_seconds,
        timeout=args.timeout,
    )

    print("Return code:", result.returncode)
    print("Report dir:", result.report_dir)
    pprint(result.metrics)
    if result.stderr.strip():
        print("\nSTDERR:\n", result.stderr)


if __name__ == "__main__":
    main()
