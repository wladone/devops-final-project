"""Table-driven edge-case coverage for every validator in
``src/data_quality_monitor/validators.py``.

This sits alongside the existing ``test_validators.py`` (happy-path
coverage) and pushes into the corner cases called out in the test plan:
case-flipped headers, NaN vs whitespace vs empty string, Unicode NFC vs
NFD, scientific notation, leap-year handling, exactly-at-threshold ratios.
"""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
import pytest

from data_quality_monitor.validators import (
    validate_allowed_values,
    validate_date_columns,
    validate_non_null_columns,
    validate_null_thresholds,
    validate_positive_numeric_columns,
    validate_required_columns,
    validate_unique_columns,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# validate_required_columns
# ---------------------------------------------------------------------------

class TestRequiredColumns:
    def test_all_present_passes(self) -> None:
        df = pd.DataFrame(columns=["band_id", "species_common"])
        result = validate_required_columns(df, ["band_id", "species_common"])[0]
        assert result.status == "PASS"
        assert result.metric_value == 0

    def test_one_missing_fails_and_names_it(self) -> None:
        df = pd.DataFrame(columns=["band_id"])
        result = validate_required_columns(df, ["band_id", "species_common"])[0]
        assert result.status == "FAIL"
        assert "species_common" in result.message
        assert result.metric_value == 1

    def test_many_missing_listed_in_order(self) -> None:
        df = pd.DataFrame(columns=["band_id"])
        result = validate_required_columns(df, ["alpha", "bravo", "charlie"])[0]
        assert result.status == "FAIL"
        assert result.metric_value == 3
        # All three missing column names appear; original order preserved
        # in the comma-joined tail of the message.
        tail = result.message.split(":", 1)[1]
        idx_a = tail.index("alpha")
        idx_b = tail.index("bravo")
        idx_c = tail.index("charlie")
        assert idx_a < idx_b < idx_c

    def test_case_mismatch_is_a_miss(self) -> None:
        """Header check is case-sensitive — ``Band_ID`` does NOT match ``band_id``."""
        df = pd.DataFrame(columns=["Band_ID"])
        result = validate_required_columns(df, ["band_id"])[0]
        assert result.status == "FAIL"


# ---------------------------------------------------------------------------
# validate_non_null_columns
# ---------------------------------------------------------------------------

class TestNonNullColumns:
    @pytest.mark.parametrize(
        "values,expected_failed",
        [
            (["a", "b", "c"], 0),
            (["a", None, "c"], 1),
            ([None, None, None], 3),
            ([np.nan, "b", np.nan], 2),
        ],
    )
    def test_null_counts(self, values: list, expected_failed: int) -> None:
        df = pd.DataFrame({"x": values})
        result = validate_non_null_columns(df, ["x"])[0]
        assert result.failed_rows == expected_failed
        assert (result.status == "PASS") == (expected_failed == 0)

    def test_empty_string_is_not_null(self) -> None:
        """``""`` is data, not NaN — this is the existing contract."""
        df = pd.DataFrame({"x": ["", "y"]})
        result = validate_non_null_columns(df, ["x"])[0]
        assert result.status == "PASS"

    def test_missing_column_is_skipped(self) -> None:
        df = pd.DataFrame({"y": ["a"]})
        assert validate_non_null_columns(df, ["x"]) == []


# ---------------------------------------------------------------------------
# validate_unique_columns
# ---------------------------------------------------------------------------

class TestUniqueColumns:
    def test_all_unique_passes(self) -> None:
        df = pd.DataFrame({"id": ["a", "b", "c"]})
        assert validate_unique_columns(df, ["id"])[0].status == "PASS"

    def test_duplicate_at_head_caught(self) -> None:
        df = pd.DataFrame({"id": ["a", "a", "b"]})
        assert validate_unique_columns(df, ["id"])[0].failed_rows == 1

    def test_duplicate_at_tail_caught(self) -> None:
        df = pd.DataFrame({"id": ["a", "b", "b"]})
        assert validate_unique_columns(df, ["id"])[0].failed_rows == 1

    def test_case_sensitive_duplicates(self) -> None:
        """``RA-1`` and ``ra-1`` are distinct values — no duplicate."""
        df = pd.DataFrame({"id": ["RA-1", "ra-1"]})
        assert validate_unique_columns(df, ["id"])[0].status == "PASS"

    def test_unicode_nfc_vs_nfd_are_distinct(self) -> None:
        """``café`` in NFC vs NFD are byte-distinct — the validator treats
        them as different values.  (Documenting current behaviour — if we
        ever want NFC normalisation, change the validator first.)"""
        nfc = unicodedata.normalize("NFC", "café")
        nfd = unicodedata.normalize("NFD", "café")
        assert nfc != nfd
        df = pd.DataFrame({"id": [nfc, nfd]})
        assert validate_unique_columns(df, ["id"])[0].status == "PASS"


# ---------------------------------------------------------------------------
# validate_positive_numeric_columns
# ---------------------------------------------------------------------------

class TestPositiveNumeric:
    @pytest.mark.parametrize(
        "value,is_valid",
        [
            (1, True),
            (3.14, True),
            ("7", True),
            ("3.0", True),
            ("1e3", True),
            (0, False),
            (-1, False),
            ("-1", False),
            ("nan", False),
            ("", False),
            ("3,5", False),  # locale comma not accepted
            ("abc", False),
        ],
    )
    def test_single_value(self, value, is_valid: bool) -> None:
        df = pd.DataFrame({"x": [value]})
        result = validate_positive_numeric_columns(df, ["x"])[0]
        assert (result.status == "PASS") == is_valid


# ---------------------------------------------------------------------------
# validate_date_columns
# ---------------------------------------------------------------------------

class TestDateColumns:
    @pytest.mark.parametrize(
        "value,is_valid",
        [
            ("2024-01-01", True),
            ("2024-02-29", True),    # leap year
            ("2025-02-29", False),   # not a leap year
            ("2025-13-01", False),   # invalid month
            ("31/12/2024", False),   # wrong format
            ("not-a-date", False),
            ("0000-00-00", False),
        ],
    )
    def test_single_value(self, value: str, is_valid: bool) -> None:
        df = pd.DataFrame({"d": [value]})
        result = validate_date_columns(df, ["d"])[0]
        assert (result.status == "PASS") == is_valid, (
            f"{value!r} expected {'PASS' if is_valid else 'FAIL'}, got {result.status}"
        )

    def test_empty_string_counts_as_null_and_passes(self) -> None:
        """``""`` is read by pandas as NaN, which the date validator treats
        as missing (not invalid)."""
        df = pd.DataFrame({"d": [""]})
        # pd.read_csv would convert "" to NaN; we mimic that here.
        df["d"] = df["d"].replace("", np.nan)
        assert validate_date_columns(df, ["d"])[0].status == "PASS"


# ---------------------------------------------------------------------------
# validate_allowed_values
# ---------------------------------------------------------------------------

class TestAllowedValues:
    def test_in_set_passes(self) -> None:
        df = pd.DataFrame({"flyway_region": ["WEU", "EAA"]})
        result = validate_allowed_values(df, {"flyway_region": ["WEU", "EAA"]})[0]
        assert result.status == "PASS"

    def test_case_mismatch_fails(self) -> None:
        """``weu`` (lowercase) is not in the ``WEU`` allowed set."""
        df = pd.DataFrame({"flyway_region": ["weu"]})
        result = validate_allowed_values(df, {"flyway_region": ["WEU"]})[0]
        assert result.status == "FAIL"

    def test_whitespace_is_significant(self) -> None:
        """`` WEU`` (leading space) is not the same as ``WEU``."""
        df = pd.DataFrame({"flyway_region": [" WEU"]})
        result = validate_allowed_values(df, {"flyway_region": ["WEU"]})[0]
        assert result.status == "FAIL"

    def test_nan_is_ignored(self) -> None:
        """NaN is treated by ``validate_non_null_columns``, not here."""
        df = pd.DataFrame({"flyway_region": [np.nan, "WEU"]})
        result = validate_allowed_values(df, {"flyway_region": ["WEU"]})[0]
        assert result.status == "PASS"


# ---------------------------------------------------------------------------
# validate_null_thresholds
# ---------------------------------------------------------------------------

class TestNullThresholds:
    @pytest.mark.parametrize(
        "nulls,total,threshold,expected",
        [
            (0, 10, 0.5, "PASS"),
            (5, 10, 0.5, "PASS"),   # exactly at threshold
            (6, 10, 0.5, "FAIL"),   # one over
            (4, 10, 0.5, "PASS"),
            (10, 10, 1.0, "PASS"),  # threshold 1.0 means anything
            (1, 10, 0.0, "FAIL"),   # threshold 0.0 means none allowed
            (0, 10, 0.0, "PASS"),
        ],
    )
    def test_at_and_around_threshold(
        self, nulls: int, total: int, threshold: float, expected: str
    ) -> None:
        values = [None] * nulls + ["x"] * (total - nulls)
        df = pd.DataFrame({"col": values})
        result = validate_null_thresholds(df, {"col": threshold})[0]
        assert result.status == expected, (
            f"{nulls}/{total} nulls @ threshold {threshold} → expected {expected}, "
            f"got {result.status} (ratio {result.metric_value})"
        )

    def test_missing_column_skipped(self) -> None:
        df = pd.DataFrame({"other": [1]})
        assert validate_null_thresholds(df, {"col": 0.5}) == []
