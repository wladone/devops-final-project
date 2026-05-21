"""Simulate disk-full while writing reports.

A real OSError(28) during ``write_reports`` must propagate, not be swallowed.
We monkey-patch ``pandas.DataFrame.to_csv`` to raise OSError mid-flight."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_quality_monitor.pipeline import run_pipeline

pytestmark = pytest.mark.chaos

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk" / "rings_control.csv"
RULES = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk" / "sparrowhawk_rules.yml"


def test_disk_full_during_csv_write_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_to_csv = pd.DataFrame.to_csv
    calls: list[int] = []

    def exploding_to_csv(self, *args, **kwargs):
        calls.append(1)
        # First call (the report CSV) succeeds — second (or first if you
        # prefer) raises ENOSPC.
        if len(calls) == 1:
            raise OSError(28, "No space left on device")
        return real_to_csv(self, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_csv", exploding_to_csv)

    with pytest.raises(OSError) as exc_info:
        run_pipeline(input_path=FIXTURE, rules_path=RULES, output_dir=tmp_path)
    assert exc_info.value.errno == 28
