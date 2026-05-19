from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import pandas as pd

from data_quality_monitor.pipeline import run_pipeline


DEFAULT_INPUT = Path("data/raw/psq_customer_base_v8_stress.csv")
DEFAULT_RULES = Path("config/rules.yml")
DEFAULT_DATA_OUTPUT_DIR = Path("data/processed/quality_ladder")
DEFAULT_REPORT_OUTPUT_ROOT = Path("reports/quality-ladder")

ALLOWED_VALUES = {
    "source": ["Way4", "PASS"],
    "country": ["NL", "BE", "FR", "LU", "ES", "DE", "GB", "AT"],
    "activity_detail_status": [
        "Active in last 12 months",
        "Inactive >12 months",
        "Never transacted",
    ],
    "merchant_activity_status": ["Active", "Inactive"],
    "type_of_activity": ["CP", "CNP", "CP+CNP"],
    "contracting_method": ["F2F", "NF2F", "F2F+NF2F"],
    "contract_status": ["Active", "Cancelled", "ActiveBO", "Entered", "Terminated"],
}

DEFAULT_VALUES = {
    "source": "PASS",
    "country": "NL",
    "activity_detail_status": "Never transacted",
    "merchant_activity_status": "Inactive",
    "type_of_activity": "CP",
    "contracting_method": "F2F",
    "contract_status": "Active",
    "last_trx_date": "2026-05-01",
    "vintage_date": "2024-01-01",
    "legal_form": "UNKNOWN_LEGAL_FORM",
    "mcc": "5999",
    "vat_number": "UNKNOWN_VAT",
    "kvk_number": "UNKNOWN_KVK",
    "active_contracts": "1",
    "contract_category_descriptions": "UNKNOWN_CATEGORY",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a progressive PSQ data-quality improvement ladder for demos."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Dirty/stress CSV input.")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES, help="Rules YAML path.")
    parser.add_argument(
        "--data-output-dir",
        type=Path,
        default=DEFAULT_DATA_OUTPUT_DIR,
        help="Directory where generated ladder CSV files are written.",
    )
    parser.add_argument(
        "--report-output-root",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT_ROOT,
        help="Directory where per-step quality reports are written.",
    )
    return parser.parse_args()


def load_dirty_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input dataset was not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")


def is_blank(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().eq("")


def set_default_when_blank(frame: pd.DataFrame, column: str, value: str) -> None:
    if column in frame.columns:
        frame.loc[is_blank(frame[column]), column] = value


def fix_missing_critical_fields(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    if "id" in result.columns:
        missing_id = is_blank(result["id"])
        result.loc[missing_id, "id"] = [
            f"UNKNOWN_ID_{index:06d}" for index in result.index[missing_id]
        ]

    if "name" in result.columns:
        missing_name = is_blank(result["name"])
        result.loc[missing_name, "name"] = [
            f"UNKNOWN_MERCHANT_{index:06d}" for index in result.index[missing_name]
        ]

    for column in [
        "source",
        "country",
        "activity_detail_status",
        "merchant_activity_status",
        "type_of_activity",
        "contracting_method",
        "contract_status",
    ]:
        set_default_when_blank(result, column, DEFAULT_VALUES[column])

    if {"source", "id", "psq_entity_key"}.issubset(result.columns):
        missing_key = is_blank(result["psq_entity_key"])
        result.loc[missing_key, "psq_entity_key"] = (
            result.loc[missing_key, "source"].astype(str) + ":" + result.loc[missing_key, "id"].astype(str)
        )

    return result


def normalize_allowed_domains(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column, allowed in ALLOWED_VALUES.items():
        if column not in result.columns:
            continue
        default_value = DEFAULT_VALUES[column]
        invalid = ~result[column].isin(allowed)
        result.loc[invalid, column] = default_value
    return result


def repair_dates_and_threshold_fields(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    for column in ["last_trx_date", "vintage_date"]:
        if column not in result.columns:
            continue
        parsed = pd.to_datetime(result[column], format="%Y-%m-%d", errors="coerce")
        invalid_or_blank = parsed.isna()
        result.loc[invalid_or_blank, column] = DEFAULT_VALUES[column]

    for column in [
        "legal_form",
        "mcc",
        "vat_number",
        "kvk_number",
        "active_contracts",
        "contract_category_descriptions",
    ]:
        set_default_when_blank(result, column, DEFAULT_VALUES[column])

    return result


def deduplicate_business_keys(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    if "id" in result.columns:
        result["id"] = result["id"].astype(str)
        duplicate_index = result.groupby("id", dropna=False).cumcount()
        duplicate_mask = duplicate_index.gt(0)
        result.loc[duplicate_mask, "id"] = (
            result.loc[duplicate_mask, "id"]
            + "-DEDUP-"
            + duplicate_index.loc[duplicate_mask].astype(str).str.zfill(3)
        )

    if {"source", "id", "psq_entity_key"}.issubset(result.columns):
        result["psq_entity_key"] = result["source"].astype(str) + ":" + result["id"].astype(str)

    if "psq_entity_key" in result.columns:
        duplicate_index = result.groupby("psq_entity_key", dropna=False).cumcount()
        duplicate_mask = duplicate_index.gt(0)
        result.loc[duplicate_mask, "psq_entity_key"] = (
            result.loc[duplicate_mask, "psq_entity_key"]
            + "-DEDUP-"
            + duplicate_index.loc[duplicate_mask].astype(str).str.zfill(3)
        )

    return result


def write_step_dataset(frame: pd.DataFrame, data_output_dir: Path, step_id: str) -> Path:
    data_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_output_dir / f"{step_id}.csv"
    frame.to_csv(output_path, index=False)
    return output_path


def summarize_step(
    *,
    step_id: str,
    title: str,
    description: str,
    input_path: Path,
    rules_path: Path,
    report_output_root: Path,
) -> dict[str, object]:
    output_dir = report_output_root / step_id
    outcome = run_pipeline(input_path=input_path, rules_path=rules_path, output_dir=output_dir)
    failed_checks = [
        f"{check['check_name']}:{check['column_name']}" for check in outcome.summary["failed_checks"]
    ]

    return {
        "step": step_id,
        "title": title,
        "description": description,
        "input_file": input_path.as_posix(),
        "output_dir": output_dir.as_posix(),
        "row_count": outcome.summary["row_count"],
        "checks_total": outcome.summary["checks_total"],
        "checks_passed": outcome.summary["checks_passed"],
        "checks_failed": outcome.summary["checks_failed"],
        "quality_score": outcome.summary["quality_score"],
        "failed_checks": failed_checks,
    }


def write_ladder_outputs(rows: list[dict[str, object]], report_output_root: Path) -> None:
    report_output_root.mkdir(parents=True, exist_ok=True)
    summary_frame = pd.DataFrame(rows)
    summary_frame["score_delta"] = summary_frame["quality_score"].diff().fillna(0).round(2)
    summary_frame["failed_delta"] = summary_frame["checks_failed"].diff().fillna(0).astype(int)

    csv_path = report_output_root / "quality_ladder_summary.csv"
    json_path = report_output_root / "quality_ladder_summary.json"
    md_path = report_output_root / "quality_ladder_summary.md"

    summary_frame.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(summary_frame.to_dict(orient="records"), indent=2), encoding="utf-8")

    markdown_lines = [
        "# PSQ Quality Improvement Ladder",
        "",
        "| Step | What changed | Score | Failed checks | Delta |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in summary_frame.itertuples(index=False):
        markdown_lines.append(
            f"| `{row.step}` | {row.title} | {row.quality_score:.2f}% | "
            f"{row.checks_failed} | {row.score_delta:+.2f} |"
        )
    md_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    dirty = load_dirty_frame(args.input)

    steps: list[tuple[str, str, str, Callable[[pd.DataFrame], pd.DataFrame]]] = [
        (
            "00_dirty_input",
            "Dirty PSQ stress input",
            "Original fake stress data before any remediation.",
            lambda frame: frame.copy(),
        ),
        (
            "01_missing_fields_fixed",
            "Fill required business fields",
            "Adds safe placeholder values for missing critical identifiers and status fields.",
            fix_missing_critical_fields,
        ),
        (
            "02_domain_values_fixed",
            "Normalize allowed values",
            "Maps unsupported countries, sources, channels, methods, and statuses into accepted domains.",
            lambda frame: normalize_allowed_domains(fix_missing_critical_fields(frame)),
        ),
        (
            "03_dates_thresholds_fixed",
            "Repair dates and completeness thresholds",
            "Fixes invalid dates and fills optional fields that breached null-rate thresholds.",
            lambda frame: repair_dates_and_threshold_fields(
                normalize_allowed_domains(fix_missing_critical_fields(frame))
            ),
        ),
        (
            "04_deduplicated_final",
            "Deduplicate business keys",
            "Keeps the repaired data and makes duplicate IDs/entity keys unique for the final clean run.",
            lambda frame: deduplicate_business_keys(
                repair_dates_and_threshold_fields(
                    normalize_allowed_domains(fix_missing_critical_fields(frame))
                )
            ),
        ),
    ]

    rows: list[dict[str, object]] = []
    for step_id, title, description, transform in steps:
        step_frame = transform(dirty)
        input_path = write_step_dataset(step_frame, args.data_output_dir, step_id)
        rows.append(
            summarize_step(
                step_id=step_id,
                title=title,
                description=description,
                input_path=input_path,
                rules_path=args.rules,
                report_output_root=args.report_output_root,
            )
        )

    write_ladder_outputs(rows, args.report_output_root)

    summary = pd.DataFrame(rows)[["step", "quality_score", "checks_failed", "checks_passed", "row_count"]]
    print("PSQ quality improvement ladder finished.")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
