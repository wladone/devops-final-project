"""Fixtures shared by the integration / golden-file tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk"
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
RULES_FILE = FIXTURE_DIR / "sparrowhawk_rules.yml"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture(scope="session")
def golden_dir() -> Path:
    return GOLDEN_DIR


@pytest.fixture(scope="session")
def rules_file() -> Path:
    return RULES_FILE
