from __future__ import annotations

import os
from pathlib import Path


def default_env() -> dict[str, str]:
    env = os.environ.copy()

    project_root = Path(__file__).resolve().parents[2]
    candidate_lib_dirs = [
        project_root / "timeloop" / "build",
        project_root / "timeloop" / "lib",
        Path("/usr/local/lib"),
    ]
    existing_lib_dirs = [str(p) for p in candidate_lib_dirs if p.exists()]

    def prepend_paths(var_name: str, paths: list[str]) -> None:
        current = env.get(var_name, "")
        current_parts = [p for p in current.split(":") if p]
        merged = [p for p in paths if p not in current_parts] + current_parts
        env[var_name] = ":".join(merged)

    prepend_paths("LD_LIBRARY_PATH", existing_lib_dirs)
    prepend_paths("DYLD_LIBRARY_PATH", existing_lib_dirs)
    prepend_paths("DYLD_FALLBACK_LIBRARY_PATH", existing_lib_dirs)

    return env
