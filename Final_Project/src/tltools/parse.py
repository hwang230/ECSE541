from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_SUMMARY_PATTERNS = (
    (_SUMMARY_RE_WITH_ALGO := re.compile(
        r"Utilization\s*=\s*(?P<util>[0-9.]+)\s*\|\s*"
        r"pJ/Algorithmic-Compute\s*=\s*(?P<pj_algo>[0-9.]+)\s*\|\s*"
        r"pJ/Compute\s*=\s*(?P<pj_compute>[0-9.]+)\s*\|\s*"
        r"Cycles\s*=\s*(?P<cycles>[0-9]+)"
    ), True),
    (_SUMMARY_RE_DENSE := re.compile(
        r"Utilization\s*=\s*(?P<util>[0-9.]+)\s*\|\s*"
        r"pJ/Compute\s*=\s*(?P<pj_compute>[0-9.]+)\s*\|\s*"
        r"Cycles\s*=\s*(?P<cycles>[0-9]+)"
    ), False),
)
_ACCELERGY_OUTPUT_SUFFIXES = {
    "ert": "ERT.yaml",
    "ert_summary": "ERT_summary.yaml",
    "art": "ART.yaml",
    "art_summary": "ART_summary.yaml",
    "flattened_architecture": "flattened_architecture.yaml",
}


def parse_timeloop_stdout(text: str, *, clock_seconds: float | None = None) -> dict[str, Any]:
    match = None
    has_algo = False
    for pattern, pattern_has_algo in _SUMMARY_PATTERNS:
        match = pattern.search(text)
        if match:
            has_algo = pattern_has_algo
            break
    if match is None:
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
        key: load_yaml_if_exists(run_dir / f"{prefix}.{suffix}")
        for key, suffix in _ACCELERGY_OUTPUT_SUFFIXES.items()
    }
