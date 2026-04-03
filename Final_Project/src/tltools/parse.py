from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_SUMMARY_RE_WITH_ALGO = re.compile(
    r"Utilization\s*=\s*(?P<util>[0-9.]+)\s*\|\s*"
    r"pJ/Algorithmic-Compute\s*=\s*(?P<pj_algo>[0-9.]+)\s*\|\s*"
    r"pJ/Compute\s*=\s*(?P<pj_compute>[0-9.]+)\s*\|\s*"
    r"Cycles\s*=\s*(?P<cycles>[0-9]+)"
)
_SUMMARY_RE_DENSE = re.compile(
    r"Utilization\s*=\s*(?P<util>[0-9.]+)\s*\|\s*"
    r"pJ/Compute\s*=\s*(?P<pj_compute>[0-9.]+)\s*\|\s*"
    r"Cycles\s*=\s*(?P<cycles>[0-9]+)"
)


def parse_timeloop_stdout(text: str, *, clock_seconds: float | None = None) -> dict[str, Any]:
    match = _SUMMARY_RE_WITH_ALGO.search(text)
    has_algo = True
    if not match:
        match = _SUMMARY_RE_DENSE.search(text)
        has_algo = False
    if not match:
        return {"raw_stdout": text, "parsed": False}

    cycles = int(match.group("cycles"))
    result: dict[str, Any] = {
        "parsed": True,
        "cycles": cycles,
        "utilization": float(match.group("util")),
        "pj_per_compute": float(match.group("pj_compute")),
        "pj_per_algorithmic_compute": (
            float(match.group("pj_algo")) if has_algo else None
        ),
    }

    if clock_seconds is not None:
        result["latency_seconds"] = cycles * clock_seconds
        result["latency_ns"] = cycles * clock_seconds * 1e9

    return result


def load_yaml_if_exists(path: str | Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_accelergy_outputs(run_dir: str | Path, prefix: str = "timeloop-model") -> dict[str, Any]:
    run_dir = Path(run_dir)
    return {
        "ert": load_yaml_if_exists(run_dir / f"{prefix}.ERT.yaml"),
        "ert_summary": load_yaml_if_exists(run_dir / f"{prefix}.ERT_summary.yaml"),
        "art": load_yaml_if_exists(run_dir / f"{prefix}.ART.yaml"),
        "art_summary": load_yaml_if_exists(run_dir / f"{prefix}.ART_summary.yaml"),
        "flattened_architecture": load_yaml_if_exists(
            run_dir / f"{prefix}.flattened_architecture.yaml"
        ),
    }
