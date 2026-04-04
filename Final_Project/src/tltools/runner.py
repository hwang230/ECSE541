from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .config import default_env
from .parse import load_accelergy_outputs, parse_timeloop_stdout


@dataclass
class CommandResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        root = Path(__file__).resolve().parents[2]
        local_timeloop = root / "timeloop"
        local_venv_bin = root / "timeloop-python" / "venv" / "bin"
        hint = (
            f"Required tool '{name}' was not found on PATH.\n"
            "Quick checks:\n"
            f"  1) Activate your venv if applicable: source {local_venv_bin}/activate\n"
            f"  2) Build Timeloop binaries in: {local_timeloop}\n"
            "     Example:\n"
            f"       cd {local_timeloop}\n"
            f"       {local_venv_bin}/scons -j4\n"
            "  3) Export PATH to include the build output directory that contains timeloop-model.\n"
            "  4) Verify with: which timeloop-model && which accelergy\n"
            "If build fails with missing headers (e.g., boost/isl/barvinok), install those dependencies first."
        )
        raise RuntimeError(hint)
    return path


def run_command(
    cmd: Sequence[str],
    cwd: str | Path | None = None,
    timeout: int = 120,
) -> CommandResult:
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd) if cwd else None,
        env=default_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CommandResult(
        cmd=list(cmd),
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def accelergy_art_from_arch(
    arch_input: str | Path,
    *,
    cwd: str | Path,
    prefix: str = "timeloop-model",
    timeout: int = 120,
) -> CommandResult:
    require_tool("accelergy")
    oprefix = prefix if prefix.endswith(".") else f"{prefix}."
    return run_command(
        [
            "accelergy",
            str(arch_input),
            "--outdir",
            ".",
            "--oprefix",
            oprefix,
            "--output_files",
            "ART",
            "ART_summary",
            "ERT",
            "ERT_summary",
            "flattened_arch",
        ],
        cwd=cwd,
        timeout=timeout,
    )


def timeloop_model_metrics(
    *inputs: str | Path,
    cwd: str | Path,
    clock_seconds: float | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    require_tool("timeloop-model")
    result = run_command(["timeloop-model", *[str(x) for x in inputs]], cwd=cwd, timeout=timeout)
    combined = "\n".join([result.stdout, result.stderr])

    metrics = parse_timeloop_stdout(combined, clock_seconds=clock_seconds)
    outputs = load_accelergy_outputs(cwd, prefix="timeloop-model")
    if outputs.get("art_summary") is None and len(inputs) >= 1:
        # Some builds do not emit ART via timeloop-model; fallback to explicit accelergy.
        accelergy_art_from_arch(inputs[0], cwd=cwd, prefix="timeloop-model", timeout=timeout)
        outputs = load_accelergy_outputs(cwd, prefix="timeloop-model")

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "metrics": metrics,
        "outputs": outputs,
    }
