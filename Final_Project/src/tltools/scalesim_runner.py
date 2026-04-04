from __future__ import annotations

import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass
class ScaleSimResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    metrics: dict[str, Any]
    report_dir: Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _local_scalesim_python() -> Path:
    return _project_root() / "timeloop-python" / "venv" / "bin" / "python"


def require_scalesim_python() -> str:
    local_python = _local_scalesim_python()
    if local_python.exists():
        return str(local_python)

    hint = (
        "Scale-Sim was not found.\n"
        "Expected local interpreter:\n"
        f"  {local_python}\n"
        "Install it into the local venv, for example:\n"
        f"  {local_python} -m pip install scalesim"
    )
    raise RuntimeError(hint)


def _write_scalesim_config(
    path: Path,
    *,
    run_name: str,
    array_rows: int,
    array_cols: int,
    ifmap_sram_kb: int,
    filter_sram_kb: int,
    ofmap_sram_kb: int,
    dataflow: str,
    bandwidths: Sequence[int],
    read_request_buffer: int = 64,
    write_request_buffer: int = 64,
) -> None:
    bw_csv = ",".join(str(int(x)) for x in bandwidths)
    text = f"""[general]
run_name = {run_name}

[run_presets]
InterfaceBandwidth = USER
UseRamulatorTrace = False

[architecture_presets]
ArrayHeight = {array_rows}
ArrayWidth = {array_cols}
ifmapsramszkB = {ifmap_sram_kb}
filtersramszkB = {filter_sram_kb}
ofmapsramszkB = {ofmap_sram_kb}
IfmapOffset = 0
FilterOffset = 10000000
OfmapOffset = 20000000
Dataflow = {dataflow}
Bandwidth = {bw_csv}
ReadRequestBuffer = {read_request_buffer}
WriteRequestBuffer = {write_request_buffer}

[layout]
IfmapCustomLayout = False
FilterCustomLayout = False
IfmapSRAMBankBandwidth = {int(bandwidths[0])}
IfmapSRAMBankNum = 1
IfmapSRAMBankPort = 2
FilterSRAMBankBandwidth = {int(bandwidths[1])}
FilterSRAMBankNum = 1
FilterSRAMBankPort = 2

[sparsity]
SparsitySupport = False
SparseRep = NONE
OptimizedMapping = False
BlockSize = 1
RandomNumberGeneratorSeed = 0
"""
    path.write_text(text, encoding="utf-8")


def _write_scalesim_topology(path: Path, *, layer_name: str, m: int, n: int, k: int) -> None:
    path.write_text(
        "Layer,M,N,K,\n"
        f"{layer_name},{m},{n},{k},\n",
        encoding="utf-8",
    )


def _write_scalesim_layout(path: Path, *, layer_name: str) -> None:
    header = (
        "Layer name,IFMAP Height Intraline Factor,IFMAP Width Intraline Factor,"
        "Filter Height Intraline Factor,Filter Width Intraline Factor,Channel Intraline Factor,"
        "Num Filter Intraline Factor,IFMAP Height Intraline Order,IFMAP Width Intraline Order,"
        "Channel Intraline Order,IFMAP Height Interline Order,IFMAP Width Interline Order,"
        "Channel Interline Order,Num Filter Intraline Order,Channel Intraline Order,"
        "Filter Height Intraline Order,Filter Width Intraline Order,Num Filter Interline Order,"
        "Channel Interline Order,Filter Height Interline Order,Filter Width Interline Order,\n"
    )
    # Custom layouts are disabled, but Scale-Sim still expects a valid layout CSV.
    row = f"{layer_name},1,1,1,1,1,1,0,1,2,0,1,2,0,1,2,3,0,1,2,3,\n"
    path.write_text(header + row, encoding="utf-8")


def _read_single_row_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_scalesim_reports(report_dir: str | Path, *, clock_seconds: float | None = None) -> dict[str, Any]:
    report_dir = Path(report_dir)
    compute = _read_single_row_csv(report_dir / "COMPUTE_REPORT.csv")
    bandwidth = _read_single_row_csv(report_dir / "BANDWIDTH_REPORT.csv")
    access = _read_single_row_csv(report_dir / "DETAILED_ACCESS_REPORT.csv")

    metrics: dict[str, Any] = {
        "total_cycles_incl_prefetch": _to_float(compute.get(" Total Cycles (incl. prefetch)")),
        "total_cycles": _to_float(compute.get(" Total Cycles")),
        "stall_cycles": _to_float(compute.get(" Stall Cycles")),
        "overall_utilization_percent": _to_float(compute.get(" Overall Util %")),
        "mapping_efficiency_percent": _to_float(compute.get(" Mapping Efficiency %")),
        "compute_utilization_percent": _to_float(compute.get(" Compute Util %")),
        "avg_ifmap_sram_bw": _to_float(bandwidth.get(" Avg IFMAP SRAM BW")),
        "avg_filter_sram_bw": _to_float(bandwidth.get(" Avg FILTER SRAM BW")),
        "avg_ofmap_sram_bw": _to_float(bandwidth.get(" Avg OFMAP SRAM BW")),
        "avg_ifmap_dram_bw": _to_float(bandwidth.get(" Avg IFMAP DRAM BW")),
        "avg_filter_dram_bw": _to_float(bandwidth.get(" Avg FILTER DRAM BW")),
        "avg_ofmap_dram_bw": _to_float(bandwidth.get(" Avg OFMAP DRAM BW")),
        "dram_ifmap_reads": _to_float(access.get(" DRAM IFMAP Reads")),
        "dram_filter_reads": _to_float(access.get(" DRAM Filter Reads")),
        "dram_ofmap_writes": _to_float(access.get(" DRAM OFMAP Writes")),
        "parsed": bool(compute),
    }

    if metrics["total_cycles"] is not None and clock_seconds is not None:
        total_cycles = float(metrics["total_cycles"])
        metrics["latency_seconds"] = total_cycles * clock_seconds
        metrics["latency_ns"] = total_cycles * clock_seconds * 1e9

    return metrics


def run_scalesim_gemm(
    *,
    run_dir: str | Path,
    m: int,
    n: int,
    k: int,
    array_rows: int,
    array_cols: int,
    ifmap_sram_kb: int,
    filter_sram_kb: int,
    ofmap_sram_kb: int,
    dataflow: str = "ws",
    bandwidths: Sequence[int] = (16, 16, 16),
    clock_seconds: float | None = None,
    save_traces: bool = False,
    timeout: int = 300,
) -> ScaleSimResult:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    run_name = "scalesim_run"
    cfg_path = run_dir / "scalesim.cfg"
    topo_path = run_dir / "scalesim_topology.csv"
    layout_path = run_dir / "scalesim_layout.csv"
    out_root = run_dir / "scalesim_out"

    _write_scalesim_config(
        cfg_path,
        run_name=run_name,
        array_rows=array_rows,
        array_cols=array_cols,
        ifmap_sram_kb=ifmap_sram_kb,
        filter_sram_kb=filter_sram_kb,
        ofmap_sram_kb=ofmap_sram_kb,
        dataflow=dataflow,
        bandwidths=bandwidths,
    )
    _write_scalesim_topology(topo_path, layer_name="gemm0", m=m, n=n, k=k)
    _write_scalesim_layout(layout_path, layer_name="gemm0")
    out_root.mkdir(parents=True, exist_ok=True)

    python_exec = require_scalesim_python()
    cmd = [
        python_exec,
        "-m",
        "scalesim.scale",
        "-t",
        str(topo_path),
        "-l",
        str(layout_path),
        "-c",
        str(cfg_path),
        "-p",
        str(out_root),
        "-i",
        "gemm",
        "-s",
        "Y" if save_traces else "N",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(run_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    report_dir = out_root / run_name
    metrics = (
        load_scalesim_reports(report_dir, clock_seconds=clock_seconds)
        if proc.returncode == 0 and report_dir.exists()
        else {"parsed": False}
    )

    return ScaleSimResult(
        cmd=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        metrics=metrics,
        report_dir=report_dir,
    )


__all__ = ["ScaleSimResult", "load_scalesim_reports", "run_scalesim_gemm"]
