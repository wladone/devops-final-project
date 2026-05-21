"""Golden-file integration tests for the data-quality pipeline.

Runs ``run_pipeline`` against every Sparrowhawk fixture, masks volatile
fields in ``summary.json`` (timestamp, absolute input path), and compares
against a baseline committed under ``tests/golden/``.

If a fixture or the pipeline legitimately changes, regenerate the baselines
with:

    python -m tests.integration.test_golden_pipeline --update

then review the diff in your PR.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from data_quality_monitor.pipeline import run_pipeline

pytestmark = pytest.mark.integration

# Fixtures that are quick enough to run in the default suite.
FAST_FIXTURES: list[str] = [
    "rings_control.csv",
    "rings_missing_critical.csv",
    "rings_duplicate_bands.csv",
    "rings_invalid_flyways.csv",
    "rings_invalid_dates.csv",
    "rings_null_breach.csv",
    "rings_mixed_extreme.csv",
]
# Heavy fixture — gated behind RUN_HEAVY_FIXTURES=1 so the default suite is snappy.
HEAVY_FIXTURES: list[str] = ["rings_large_volume.csv"]


def _mask(summary: dict[str, Any]) -> dict[str, Any]:
    """Drop fields that legitimately change run-to-run."""
    masked = dict(summary)
    masked.pop("generated_at_utc", None)
    if "input_file" in masked:
        masked["input_file"] = Path(masked["input_file"]).name
    return masked


def _baseline_path(golden_dir: Path, fixture_name: str) -> Path:
    return golden_dir / f"{Path(fixture_name).stem}.summary.json"


def _run(fixture_dir: Path, rules_file: Path, name: str, tmp_path: Path) -> dict[str, Any]:
    outcome = run_pipeline(
        input_path=fixture_dir / name,
        rules_path=rules_file,
        output_dir=tmp_path,
    )
    return _mask(outcome.summary)


@pytest.mark.parametrize("fixture_name", FAST_FIXTURES)
def test_summary_matches_golden(
    fixture_name: str,
    fixture_dir: Path,
    golden_dir: Path,
    rules_file: Path,
    tmp_path: Path,
) -> None:
    actual = _run(fixture_dir, rules_file, fixture_name, tmp_path)
    baseline = _baseline_path(golden_dir, fixture_name)
    assert baseline.exists(), (
        f"Missing baseline {baseline}. Regenerate with: "
        f"python -m tests.integration.test_golden_pipeline --update"
    )
    expected = json.loads(baseline.read_text(encoding="utf-8"))
    assert actual == expected, (
        f"Pipeline output diverged from {baseline.name}. Inspect the diff and, "
        f"if intended, re-run with --update."
    )


@pytest.mark.skipif(
    os.environ.get("RUN_HEAVY_FIXTURES") != "1",
    reason="Set RUN_HEAVY_FIXTURES=1 to include the 60k-row scenario.",
)
@pytest.mark.parametrize("fixture_name", HEAVY_FIXTURES)
def test_summary_matches_golden_heavy(
    fixture_name: str,
    fixture_dir: Path,
    golden_dir: Path,
    rules_file: Path,
    tmp_path: Path,
) -> None:
    actual = _run(fixture_dir, rules_file, fixture_name, tmp_path)
    baseline = _baseline_path(golden_dir, fixture_name)
    assert baseline.exists(), f"Missing heavy baseline {baseline}."
    expected = json.loads(baseline.read_text(encoding="utf-8"))
    assert actual == expected


# ---------------------------------------------------------------------------
# Baseline regeneration (developer tool — not invoked by pytest)
# ---------------------------------------------------------------------------

def _regenerate_baselines() -> None:
    from tests.integration.conftest import FIXTURE_DIR, GOLDEN_DIR, RULES_FILE  # noqa: E402

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    all_fixtures = FAST_FIXTURES + HEAVY_FIXTURES
    for name in all_fixtures:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            masked = _run(FIXTURE_DIR, RULES_FILE, name, Path(tmp))
        path = _baseline_path(GOLDEN_DIR, name)
        path.write_text(json.dumps(masked, indent=2, sort_keys=True), encoding="utf-8")
        print(f"  wrote {path.relative_to(GOLDEN_DIR.parent.parent)}")


if __name__ == "__main__":
    if "--update" in sys.argv:
        _regenerate_baselines()
    else:
        print("Run with --update to regenerate golden baselines.", file=sys.stderr)
        sys.exit(2)
