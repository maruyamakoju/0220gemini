from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import platform
import subprocess
import sys


RESULT_SCHEMA_VERSION = 2
EVIDENCE_MANIFEST_VERSION = 2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_pyproject_version() -> str:
    pyproject = _repo_root() / "pyproject.toml"
    if not pyproject.exists():
        return "0+unknown"
    for raw in pyproject.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("version") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "0+unknown"


def get_genieguard_version() -> str:
    try:
        return version("genieguard")
    except PackageNotFoundError:
        return _read_pyproject_version()


def get_git_sha() -> str:
    env_sha = os.getenv("GITHUB_SHA", "").strip()
    if env_sha:
        return env_sha
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
        value = completed.stdout.strip()
        return value or "unknown"
    except Exception:
        return "unknown"


def build_runtime_meta() -> dict[str, str]:
    return {
        "genieguard_version": get_genieguard_version(),
        "git_sha": get_git_sha(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split(" ", maxsplit=1)[0],
        "platform": platform.platform(),
    }
