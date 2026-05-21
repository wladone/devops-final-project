from __future__ import annotations

import json
import os
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
    # Full sort key — including check_name — so two checks against the same
    # column (e.g. non_null and unique_key on band_id, both FAIL/critical)
    # have a deterministic order in the report.  Without check_name, the
    # tie-break depended on input order and diffs across runs were noisy.
    return frame.sort_values(
        by=["status", "severity", "column_name", "check_name"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)


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


def _atomic_replace(tmp_path: Path, final_path: Path) -> None:
    """Rename ``tmp_path`` to ``final_path`` atomically.

    ``os.replace`` is atomic on POSIX and on NTFS when both paths are on the
    same volume (the case here — we always write the temp file in the same
    directory as the final artefact)."""
    os.replace(tmp_path, final_path)


def write_reports(
    report_frame: pd.DataFrame, summary: dict[str, Any], output_dir: str | Path
) -> dict[str, Path]:
    """Write the three report artefacts atomically.

    Each artefact is first streamed to ``<name>.tmp`` in the target directory,
    then ``os.replace``-d into place.  If any write fails, every tmp file is
    cleaned up so the output directory never contains a half-written report
    next to a stale one from a previous run.
    """
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    csv_path = target_dir / "quality_report.csv"
    json_path = target_dir / "summary.json"
    xlsx_path = target_dir / "quality_report.xlsx"

    # Unique-per-writer tmp suffix so concurrent runs to the same output_dir
    # don't collide on the tmp filename and corrupt each other's mid-write
    # state.  Uses pid + monotonic ns; both are cheap and lock-free.
    import threading
    import time
    suffix = f".{os.getpid()}.{threading.get_ident()}.{time.monotonic_ns()}.tmp"
    csv_tmp = csv_path.with_suffix(csv_path.suffix + suffix)
    json_tmp = json_path.with_suffix(json_path.suffix + suffix)
    xlsx_tmp = xlsx_path.with_suffix(xlsx_path.suffix + suffix)
    tmp_paths = (csv_tmp, json_tmp, xlsx_tmp)

    try:
        report_frame.to_csv(csv_tmp, index=False)

        with json_tmp.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)

        summary_for_excel = {key: value for key, value in summary.items() if key != "failed_checks"}
        summary_frame = pd.DataFrame([summary_for_excel])

        with pd.ExcelWriter(xlsx_tmp, engine="openpyxl") as writer:
            summary_frame.to_excel(writer, sheet_name="summary", index=False)
            report_frame.to_excel(writer, sheet_name="checks", index=False)

        # All three writes succeeded — promote in one batch.
        _atomic_replace(csv_tmp, csv_path)
        _atomic_replace(json_tmp, json_path)
        _atomic_replace(xlsx_tmp, xlsx_path)
    except BaseException:
        # On any failure, scrub the partial tmp files so the next run is clean.
        for tmp in tmp_paths:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return {
        "csv": csv_path,
        "json": json_path,
        "xlsx": xlsx_path,
    }

