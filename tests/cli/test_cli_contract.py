"""CLI contract tests for ``python -m data_quality_monitor``.

These tests exercise the binary as a black box and assert on:
- exit codes (0 on success, non-zero on misconfiguration);
- presence of the three documented flags in --help;
- a stable stdout layout (5 specific lines, in order) — what downstream
  scripts and Jenkins log parsers depend on;
- deterministic re-runs (same inputs → same exit code).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.cli

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk"
RULES_FILE = FIXTURE_DIR / "sparrowhawk_rules.yml"


def _env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "data_quality_monitor", *args],
        cwd=cwd or REPO_ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------

def test_help_exits_zero_and_lists_all_flags() -> None:
    result = _run(["--help"])
    assert result.returncode == 0, result.stderr
    for flag in ("--input", "--rules", "--output-dir"):
        assert flag in result.stdout, f"Expected {flag!r} in --help output"


# ---------------------------------------------------------------------------
# Bad config / inputs
# ---------------------------------------------------------------------------

def test_missing_rules_file_exits_non_zero() -> None:
    result = _run(["--rules", "config/does-not-exist.yml"])
    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "no such file" in combined or "errno 2" in combined or "filenotfound" in combined


def test_unsupported_input_format_exits_non_zero(tmp_path: Path) -> None:
    bogus = tmp_path / "data.parquet"
    bogus.write_bytes(b"not really parquet")
    result = _run(["--rules", str(RULES_FILE), "--input", str(bogus)])
    assert result.returncode != 0
    assert "unsupported file format" in (result.stdout + result.stderr).lower()


# ---------------------------------------------------------------------------
# Happy-path stdout contract
# ---------------------------------------------------------------------------

EXPECTED_LINE_PATTERNS = [
    re.compile(r"^Data quality checks finished\.$"),
    re.compile(r"^Rows processed: \d+$"),
    re.compile(r"^Checks passed: \d+$"),
    re.compile(r"^Checks failed: \d+$"),
    re.compile(r"^Quality score: \d+(\.\d+)?%$"),
]


def test_happy_path_stdout_layout(tmp_path: Path) -> None:
    fixture = FIXTURE_DIR / "rings_control.csv"
    result = _run([
        "--rules", str(RULES_FILE),
        "--input", str(fixture),
        "--output-dir", str(tmp_path),
    ])
    assert result.returncode == 0, result.stderr

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    # First five non-blank lines must match the documented contract, in order.
    for pattern, line in zip(EXPECTED_LINE_PATTERNS, lines[:5]):
        assert pattern.match(line), f"Stdout line {line!r} did not match {pattern.pattern!r}"

    # Three output files were announced.
    tail = "\n".join(lines[5:])
    for name in ("csv", "json", "xlsx"):
        assert f"- {name}:" in tail, f"Expected '- {name}:' line in announce block"

    # And the three files exist on disk.
    assert (tmp_path / "quality_report.csv").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "quality_report.xlsx").exists()


def test_two_runs_produce_identical_exit_code(tmp_path: Path) -> None:
    fixture = FIXTURE_DIR / "rings_control.csv"
    args = [
        "--rules", str(RULES_FILE),
        "--input", str(fixture),
        "--output-dir", str(tmp_path),
    ]
    a = _run(args)
    b = _run(args)
    assert a.returncode == b.returncode == 0
