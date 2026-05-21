"""Regenerate ``tests/perf/baseline.json`` from a fresh local run.

Use sparingly — only after a deliberate, reviewed performance change.
"""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path

from data_quality_monitor.pipeline import run_pipeline

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk"
RULES = FIXTURE_DIR / "sparrowhawk_rules.yml"
BASELINE_PATH = REPO_ROOT / "tests" / "perf" / "baseline.json"

FIXTURES = {
    "rings_control": 5,
    "rings_mixed_extreme": 5,
    "rings_large_volume": 3,
}


def _measure(fixture_name: str, rounds: int) -> float:
    samples: list[float] = []
    for _ in range(rounds):
        with tempfile.TemporaryDirectory() as tmp:
            t0 = time.perf_counter()
            run_pipeline(input_path=FIXTURE_DIR / f"{fixture_name}.csv", rules_path=RULES, output_dir=Path(tmp))
            samples.append(time.perf_counter() - t0)
    return statistics.median(samples)


def main() -> None:
    existing = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    updated = dict(existing)
    for stem, rounds in FIXTURES.items():
        median = _measure(stem, rounds)
        updated["fixtures"][stem]["median_seconds"] = round(median, 2)
        print(f"  {stem}: {median:.3f}s")
    BASELINE_PATH.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    print(f"\nWrote {BASELINE_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
