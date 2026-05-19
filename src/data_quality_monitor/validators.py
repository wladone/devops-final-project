from __future__ import annotations

from typing import Iterable

import pandas as pd

from data_quality_monitor.config import DataQualityRules
from data_quality_monitor.models import CheckResult


def _intersection(columns: Iterable[str], frame: pd.DataFrame) -> list[str]:
    frame_columns = set(frame.columns)
    return [column for column in columns if column in frame_columns]


def validate_required_columns(df: pd.DataFrame, required_columns: list[str]) -> list[CheckResult]:
    missing_columns = [column for column in required_columns if column not in df.columns]
    status = "PASS" if not missing_columns else "FAIL"
    message = (
        "All required columns are present."
        if not missing_columns
        else f"Missing required columns: {', '.join(missing_columns)}."
    )
    return [
        CheckResult(
            check_name="required_columns_present",
            column_name="dataset",
            status=status,
            severity="critical",
            metric_value=len(missing_columns),
            threshold=0,
            failed_rows=0,
            message=message,
        )
    ]


def validate_non_null_columns(df: pd.DataFrame, columns: list[str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for column in _intersection(columns, df):
        null_count = int(df[column].isna().sum())
        status = "PASS" if null_count == 0 else "FAIL"
        results.append(
            CheckResult(
                check_name="non_null",
                column_name=column,
                status=status,
                severity="critical",
                metric_value=null_count,
                threshold=0,
                failed_rows=null_count,
                message=(
                    f"Column '{column}' has no null values."
                    if null_count == 0
                    else f"Column '{column}' contains {null_count} null values."
                ),
            )
        )
    return results


def validate_unique_columns(df: pd.DataFrame, columns: list[str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for column in _intersection(columns, df):
        duplicate_count = int(df.duplicated(subset=[column]).sum())
        status = "PASS" if duplicate_count == 0 else "FAIL"
        results.append(
            CheckResult(
                check_name="unique_key",
                column_name=column,
                status=status,
                severity="critical",
                metric_value=duplicate_count,
                threshold=0,
                failed_rows=duplicate_count,
                message=(
                    f"Column '{column}' is unique."
                    if duplicate_count == 0
                    else f"Column '{column}' contains {duplicate_count} duplicate rows."
                ),
            )
        )
    return results


def validate_positive_numeric_columns(df: pd.DataFrame, columns: list[str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for column in _intersection(columns, df):
        numeric_series = pd.to_numeric(df[column], errors="coerce")
        invalid_mask = numeric_series.isna() | (numeric_series <= 0)
        invalid_count = int(invalid_mask.sum())
        status = "PASS" if invalid_count == 0 else "FAIL"
        results.append(
            CheckResult(
                check_name="positive_numeric",
                column_name=column,
                status=status,
                severity="critical",
                metric_value=invalid_count,
                threshold=0,
                failed_rows=invalid_count,
                message=(
                    f"Column '{column}' contains only positive numbers."
                    if invalid_count == 0
                    else f"Column '{column}' contains {invalid_count} values that are non-numeric or <= 0."
                ),
            )
        )
    return results


def validate_date_columns(df: pd.DataFrame, columns: list[str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for column in _intersection(columns, df):
        parsed = pd.to_datetime(df[column], errors="coerce", format="%Y-%m-%d")
        invalid_mask = parsed.isna() & df[column].notna()
        invalid_count = int(invalid_mask.sum())
        status = "PASS" if invalid_count == 0 else "FAIL"
        results.append(
            CheckResult(
                check_name="valid_date",
                column_name=column,
                status=status,
                severity="critical",
                metric_value=invalid_count,
                threshold=0,
                failed_rows=invalid_count,
                message=(
                    f"Column '{column}' contains only valid dates."
                    if invalid_count == 0
                    else f"Column '{column}' contains {invalid_count} invalid date values."
                ),
            )
        )
    return results


def validate_allowed_values(
    df: pd.DataFrame, allowed_values: dict[str, list[str]]
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for column, valid_values in allowed_values.items():
        if column not in df.columns:
            continue
        invalid_mask = ~df[column].isin(valid_values) & df[column].notna()
        invalid_count = int(invalid_mask.sum())
        status = "PASS" if invalid_count == 0 else "FAIL"
        results.append(
            CheckResult(
                check_name="allowed_values",
                column_name=column,
                status=status,
                severity="warning",
                metric_value=invalid_count,
                threshold=", ".join(valid_values),
                failed_rows=invalid_count,
                message=(
                    f"Column '{column}' stays within the allowed values."
                    if invalid_count == 0
                    else f"Column '{column}' contains {invalid_count} values outside: {', '.join(valid_values)}."
                ),
            )
        )
    return results


def validate_null_thresholds(
    df: pd.DataFrame, thresholds: dict[str, float]
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for column, threshold in thresholds.items():
        if column not in df.columns:
            continue
        null_ratio = float(df[column].isna().mean())
        status = "PASS" if null_ratio <= threshold else "FAIL"
        results.append(
            CheckResult(
                check_name="null_threshold",
                column_name=column,
                status=status,
                severity="warning",
                metric_value=round(null_ratio, 4),
                threshold=threshold,
                failed_rows=int(df[column].isna().sum()),
                message=(
                    f"Column '{column}' is within the configured null threshold."
                    if status == "PASS"
                    else f"Column '{column}' exceeds the null threshold: {null_ratio:.2%} > {threshold:.2%}."
                ),
            )
        )
    return results


def run_validation_checks(df: pd.DataFrame, rules: DataQualityRules) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(validate_required_columns(df, rules.required_columns))
    results.extend(validate_non_null_columns(df, rules.non_null_columns))
    results.extend(validate_unique_columns(df, rules.unique_columns))
    results.extend(validate_positive_numeric_columns(df, rules.positive_numeric_columns))
    results.extend(validate_date_columns(df, rules.date_columns))
    results.extend(validate_allowed_values(df, rules.allowed_values))
    results.extend(validate_null_thresholds(df, rules.null_thresholds))
    return results
