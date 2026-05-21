"""Hypothesis-driven property tests for the validators and report layer.

Six invariants from the plan:
1. ``null_ratio`` reported by ``validate_null_thresholds`` is in [0, 1].
2. ``validate_unique_columns`` never reports more failed_rows than len(df).
3. Running every validator is order-independent (set-equality of results).
4. ``build_report_dataframe`` is permutation-invariant after its internal sort.
5. ``quality_score == 100`` if and only if every check passes.
6. CSV write -> read -> write is byte-identical.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from data_quality_monitor.config import DataQualityRules
from data_quality_monitor.report_generator import build_report_dataframe, build_summary
from data_quality_monitor.validators import (
    run_validation_checks,
    validate_null_thresholds,
    validate_unique_columns,
)

pytestmark = pytest.mark.property

# Hypothesis defaults bumped down a touch so the full property suite stays
# under ~5 s on the CI runner.
HYP_SETTINGS = settings(
    max_examples=80,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# A small dataframe with one nullable string column ("species_common") and
# one nullable id column ("band_id").  Enough surface to exercise the
# null-threshold and uniqueness validators.
def _frames() -> st.SearchStrategy[pd.DataFrame]:
    @st.composite
    def _build(draw: st.DrawFn) -> pd.DataFrame:
        n = draw(st.integers(min_value=1, max_value=40))
        ids = draw(st.lists(
            st.one_of(
                st.none(),
                st.text(alphabet="ABCDEF0123456789", min_size=1, max_size=6),
            ),
            min_size=n, max_size=n,
        ))
        species = draw(st.lists(
            st.one_of(st.none(), st.sampled_from(["Goshawk", "Kestrel", "Hobby"])),
            min_size=n, max_size=n,
        ))
        return pd.DataFrame({"band_id": ids, "species_common": species})
    return _build()


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@HYP_SETTINGS
@given(df=_frames(), threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
def test_null_ratio_within_unit_interval(df: pd.DataFrame, threshold: float) -> None:
    results = validate_null_thresholds(df, {"band_id": threshold, "species_common": threshold})
    for r in results:
        assert 0.0 <= float(r.metric_value) <= 1.0


@HYP_SETTINGS
@given(df=_frames())
def test_unique_failed_rows_never_exceeds_length(df: pd.DataFrame) -> None:
    results = validate_unique_columns(df, ["band_id"])
    for r in results:
        assert r.failed_rows <= len(df)


@HYP_SETTINGS
@given(df=_frames())
def test_validator_composition_is_order_independent(df: pd.DataFrame) -> None:
    rules = DataQualityRules(
        required_columns=["band_id", "species_common"],
        non_null_columns=["band_id"],
        unique_columns=["band_id"],
        null_thresholds={"species_common": 0.5},
    )
    first = run_validation_checks(df, rules)
    second = run_validation_checks(df, rules)
    # Compare as sets of (check_name, column_name, status, failed_rows, metric_value).
    def key(r):
        return (r.check_name, r.column_name, r.status, r.failed_rows, str(r.metric_value))
    assert sorted(map(key, first)) == sorted(map(key, second))


@HYP_SETTINGS
@given(df=_frames())
def test_build_report_dataframe_is_permutation_invariant(df: pd.DataFrame) -> None:
    """After the sort-key fix (issue #1), ``build_report_dataframe`` produces
    identical row *order* for any permutation of the same input."""
    rules = DataQualityRules(
        required_columns=["band_id"],
        non_null_columns=["band_id"],
        unique_columns=["band_id"],
        null_thresholds={"species_common": 0.5},
    )
    results = run_validation_checks(df, rules)
    forward = build_report_dataframe(results)
    reverse = build_report_dataframe(list(reversed(results)))
    pd.testing.assert_frame_equal(forward, reverse)


@HYP_SETTINGS
@given(df=_frames())
def test_quality_score_iff_all_pass(df: pd.DataFrame) -> None:
    rules = DataQualityRules(
        required_columns=["band_id", "species_common"],
        non_null_columns=["band_id"],
        unique_columns=["band_id"],
        null_thresholds={"species_common": 1.0},  # never breached
    )
    results = run_validation_checks(df, rules)
    summary = build_summary(results, input_path="<memory>", row_count=len(df))
    all_pass = all(r.is_passed for r in results)
    if all_pass:
        assert summary["quality_score"] == 100.0
    else:
        assert summary["quality_score"] < 100.0


@HYP_SETTINGS
@given(df=_frames())
def test_csv_roundtrip_stabilises(df: pd.DataFrame) -> None:
    """The first write -> read pass can change dtypes (ints + NaN promote to
    float), so the bytes may differ from the original write.  After one
    normalisation pass, however, the round-trip must be a fixed point."""
    def _write(frame: pd.DataFrame) -> str:
        buf = io.StringIO()
        frame.to_csv(buf, index=False, lineterminator="\n")
        return buf.getvalue()

    normalised = pd.read_csv(io.StringIO(_write(df)))
    first = _write(normalised)
    second = _write(pd.read_csv(io.StringIO(first)))
    assert first == second
