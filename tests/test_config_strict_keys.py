"""Unit tests for the strict-key contract on ``load_config`` (issue #6).

Before the fix, a typo in ``rules.yml`` (``null_threshholds`` instead of
``null_thresholds``) was silently ignored — the misspelt check never ran
and the report looked clean.  The contract now rejects unknown keys at
load time so typos surface immediately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from data_quality_monitor.config import UnknownConfigKeyError, load_config

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, body: str) -> Path:
    rules = tmp_path / "rules.yml"
    rules.write_text(body, encoding="utf-8")
    return rules


def test_unknown_top_level_key_rejected(tmp_path: Path) -> None:
    rules = _write(tmp_path, "datasett:\n  input_path: x.csv\nchecks: {}\n")
    with pytest.raises(UnknownConfigKeyError) as exc_info:
        load_config(rules)
    assert "datasett" in str(exc_info.value)


def test_unknown_dataset_key_rejected(tmp_path: Path) -> None:
    rules = _write(
        tmp_path,
        "dataset:\n  input_path: x.csv\n  output_dir: out\n  output_directory: extra\n"
        "checks: {}\n",
    )
    with pytest.raises(UnknownConfigKeyError) as exc_info:
        load_config(rules)
    assert "output_directory" in str(exc_info.value)


def test_unknown_check_key_rejected(tmp_path: Path) -> None:
    """The exact bug the fix targets: ``null_threshholds`` (typo)."""
    rules = _write(
        tmp_path,
        "dataset:\n  input_path: x.csv\nchecks:\n  required_columns: [a]\n"
        "  null_threshholds: {a: 0.5}\n",
    )
    with pytest.raises(UnknownConfigKeyError) as exc_info:
        load_config(rules)
    assert "null_threshholds" in str(exc_info.value)


def test_valid_keys_load_cleanly(tmp_path: Path) -> None:
    rules = _write(
        tmp_path,
        "dataset:\n  input_path: x.csv\n  output_dir: out\n  dtypes: {band_id: str}\n"
        "checks:\n  required_columns: [band_id]\n  null_thresholds: {band_id: 0.5}\n",
    )
    cfg = load_config(rules)
    assert cfg.dataset.dtypes == {"band_id": "str"}
    assert cfg.checks.null_thresholds == {"band_id": 0.5}
