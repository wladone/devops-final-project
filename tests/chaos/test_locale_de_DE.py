"""Numeric validators must not be fooled by locale-specific decimal commas.

A German-locale system writing ``3,5`` (= 3.5) into a numeric column should
*fail* ``validate_positive_numeric_columns`` rather than silently parse as
"3" (an integer)."""

from __future__ import annotations

import pandas as pd
import pytest

from data_quality_monitor.validators import validate_positive_numeric_columns

pytestmark = pytest.mark.chaos


def test_locale_comma_decimals_are_rejected_as_non_numeric() -> None:
    """``pd.to_numeric(..., errors='coerce')`` returns NaN for ``"3,5"``,
    so the validator should flag it as invalid."""
    df = pd.DataFrame({"active_resights": ["3,5", "1,25", "2", "7"]})
    results = validate_positive_numeric_columns(df, ["active_resights"])
    assert len(results) == 1
    result = results[0]
    assert result.status == "FAIL", "Locale-comma decimals were silently accepted"
    assert result.failed_rows == 2, f"Expected 2 invalid rows, got {result.failed_rows}"


def test_scientific_notation_is_accepted_as_numeric() -> None:
    """``1e3`` and ``2.5e-1`` are legitimate numbers and should pass."""
    df = pd.DataFrame({"active_resights": ["1e3", "2.5e-1", "7"]})
    results = validate_positive_numeric_columns(df, ["active_resights"])
    assert results[0].status == "PASS"
