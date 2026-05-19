from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from data_quality_monitor.models import CheckResult


REPORT_COLUMNS = [
    "check_name",
    "column_name",
    "status",
    "severity",
    "metric_value",
    "threshold",
    "failed_rows",
    "message",
]


def build_report_dataframe(results: list[CheckResult]) -> pd.DataFrame:
    if not results:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    frame = pd.DataFrame([result.to_record() for result in results], columns=REPORT_COLUMNS)
    return frame.sort_values(by=["status", "severity", "column_name"], ascending=[True, True, True])


def build_summary(
    results: list[CheckResult], input_path: str | Path, row_count: int
) -> dict[str, Any]:
    total_checks = len(results)
    passed_checks = sum(result.is_passed for result in results)
    failed_results = [result.to_record() for result in results if not result.is_passed]
    quality_score = round((passed_checks / total_checks) * 100, 2) if total_checks else 100.0

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path),
        "row_count": row_count,
        "checks_total": total_checks,
        "checks_passed": passed_checks,
        "checks_failed": len(failed_results),
        "quality_score": quality_score,
        "failed_checks": failed_results,
    }


def write_reports(
    report_frame: pd.DataFrame, summary: dict[str, Any], output_dir: str | Path
) -> dict[str, Path]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    csv_path = target_dir / "quality_report.csv"
    json_path = target_dir / "summary.json"
    xlsx_path = target_dir / "quality_report.xlsx"

    report_frame.to_csv(csv_path, index=False)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    summary_for_excel = {key: value for key, value in summary.items() if key != "failed_checks"}
    summary_frame = pd.DataFrame([summary_for_excel])

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary_frame.to_excel(writer, sheet_name="summary", index=False)
        report_frame.to_excel(writer, sheet_name="checks", index=False)

    return {
        "csv": csv_path,
        "json": json_path,
        "xlsx": xlsx_path,
    }

