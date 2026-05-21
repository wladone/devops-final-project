"""Performance benchmarks for ``run_pipeline``.

Each benchmark measures the wall-clock cost of running the full pipeline
(load -> validate -> write) against one of the Sparrowhawk fixtures.

The regression gate (``baseline.json``) treats a 25% slowdown vs the
committed median as a CI failure.  Update the baseline only after a
deliberate, reviewed perf change:

    python -m tests.perf.update_baseline
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from data_quality_monitor.pipeline import run_pipeline

pytestmark = pytest.mark.perf

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk"
RULES = FIXTURE_DIR / "sparrowhawk_rules.yml"
BASELINE = json.loads((REPO_ROOT / "tests" / "perf" / "baseline.json").read_text(encoding="utf-8"))


def _budget(fixture_stem: str) -> float:
    entry = BASELINE["fixtures"][fixture_stem]
    return float(entry["median_seconds"]) * float(BASELINE["tolerance_multiplier"])


def _run_pipeline_against(fixture_name: str, tmp_path: Path) -> None:
    run_pipeline(
        input_path=FIXTURE_DIR / fixture_name,
        rules_path=RULES,
        output_dir=tmp_path,
    )


@pytest.mark.parametrize("fixture_stem", ["rings_control", "rings_mixed_extreme"])
def test_pipeline_benchmark_small_and_medium(
    benchmark, fixture_stem: str, tmp_path: Path
) -> None:
    # pytest-benchmark uses a sub-second timer; cap rounds to keep the
    # default test run quick (each fixture under ~5 s wall-time).
    benchmark.pedantic(
        _run_pipeline_against,
        args=(f"{fixture_stem}.csv", tmp_path),
        rounds=3,
        warmup_rounds=1,
        iterations=1,
    )
    median = benchmark.stats.stats.median
    budget = _budget(fixture_stem)
    assert median <= budget, (
        f"{fixture_stem} median {median:.3f}s exceeded budget {budget:.3f}s "
        f"(baseline {BASELINE['fixtures'][fixture_stem]['median_seconds']}s × "
        f"{BASELINE['tolerance_multiplier']}). Investigate the regression."
    )


@pytest.mark.skipif(
    os.environ.get("RUN_HEAVY_FIXTURES") != "1",
    reason="Set RUN_HEAVY_FIXTURES=1 to benchmark the 60k-row scenario.",
)
def test_pipeline_benchmark_large_volume(benchmark, tmp_path: Path) -> None:
    benchmark.pedantic(
        _run_pipeline_against,
        args=("rings_large_volume.csv", tmp_path),
        rounds=2,
        warmup_rounds=1,
        iterations=1,
    )
    median = benchmark.stats.stats.median
    budget = _budget("rings_large_volume")
    assert median <= budget, (
        f"rings_large_volume median {median:.3f}s exceeded budget {budget:.3f}s."
    )
