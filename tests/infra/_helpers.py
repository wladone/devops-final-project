"""Shared helpers for infra validation tests.

Each test skips itself when its external tool isn't installed, so the suite
stays green on developer machines while still gating in CI (where every
tool is present).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def require(tool: str) -> str:
    """Return the path to *tool*, or skip the calling test."""
    path = shutil.which(tool)
    if not path:
        pytest.skip(f"{tool!r} is not installed on this machine")
    return path


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
