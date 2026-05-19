from pathlib import Path

import pandas as pd

from data_quality_monitor.models import CheckResult
from data_quality_monitor.report_generator import (
    REPORT_COLUMNS,
    build_report_dataframe,
    build_summary,
    write_reports,
)


def make_result(name: str, status: str, column: str = "customer_id") -> CheckResult:
    return CheckResult(
        check_name=name,
        column_name=column,
        status=status,
        severity="HIGH",
        metric_value=0,
        threshold=0,
        failed_rows=0 if status == "PASS" else 3,
        message=f"{name} {status}",
    )


def test_check_result_record_and_pass_status() -> None:
    result = make_result("non_null", "PASS")

    assert result.is_passed is True
    assert result.to_record()["check_name"] == "non_null"
    assert result.to_record()["status"] == "PASS"


def test_build_report_dataframe_keeps_expected_columns_for_empty_results() -> None:
    frame = build_report_dataframe([])

    assert list(frame.columns) == REPORT_COLUMNS
    assert frame.empty


def test_build_summary_calculates_quality_score_and_failed_checks(tmp_path: Path) -> None:
    results = [
        make_result("required_columns_present", "PASS", "dataset"),
        make_result("unique_key", "FAIL", "psq_entity_key"),
        make_result("allowed_values", "PASS", "country"),
    ]

    summary = build_summary(results, tmp_path / "customers.csv", row_count=42)

    assert summary["row_count"] == 42
    assert summary["checks_total"] == 3
    assert summary["checks_passed"] == 2
    assert summary["checks_failed"] == 1
    assert summary["quality_score"] == 66.67
    assert summary["failed_checks"][0]["check_name"] == "unique_key"


def test_write_reports_creates_csv_json_and_excel(tmp_path: Path) -> None:
    report_frame = pd.DataFrame([make_result("non_null", "PASS").to_record()])
    summary = build_summary([make_result("non_null", "PASS")], "customers.csv", row_count=1)

    paths = write_reports(report_frame, summary, tmp_path)

    assert paths["csv"].exists()
    assert paths["json"].exists()
    assert paths["xlsx"].exists()
    assert set(paths) == {"csv", "json", "xlsx"}
