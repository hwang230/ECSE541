from __future__ import annotations

import os
from pathlib import Path


def _prepend_paths(env: dict[str, str], var_name: str, paths: list[str]) -> None:
    current_parts = [p for p in env.get(var_name, "").split(":") if p]
    merged = [p for p in paths if p not in current_parts] + current_parts
    env[var_name] = ":".join(merged)


def default_env() -> dict[str, str]:
    env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[2]
    lib_dirs = [
        project_root / "timeloop" / "build",
        project_root / "timeloop" / "lib",
        Path("/usr/local/lib"),
    ]
    existing_lib_dirs = [str(path) for path in lib_dirs if path.exists()]

    for var_name in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH"):
        _prepend_paths(env, var_name, existing_lib_dirs)

    return env
