from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_SOURCE = Path("data/raw/psq_customer_base_v8.csv")
DEFAULT_OUTPUT_DIR = Path("data/stress")
DEFAULT_PRIMARY_STRESS = Path("data/raw/psq_customer_base_v8_stress.csv")

VALID_SOURCES = ["Way4", "PASS"]
VALID_COUNTRIES = ["NL", "BE", "FR", "LU", "ES", "DE", "GB", "AT"]
VALID_ACTIVITY_DETAIL_STATUSES = [
    "Active in last 12 months",
    "Inactive >12 months",
    "Never transacted",
]
VALID_MERCHANT_ACTIVITY_STATUSES = ["Active", "Inactive"]
VALID_ACTIVITY_TYPES = ["CP", "CNP", "CP+CNP"]
VALID_CONTRACTING_METHODS = ["F2F", "NF2F", "F2F+NF2F"]
VALID_CONTRACT_STATUSES = ["Active", "Cancelled", "ActiveBO", "Entered", "Terminated"]

LEGAL_FORMS = ["BV", "NV", "GMBH", "SARL", "SA", "LTD", "SAS", "SOLE_TRADER"]
MCC_CODES = ["5411", "5812", "5999", "5732", "7011", "7999", "4121", "4900"]
CONTRACT_CATEGORIES = [
    "Retail payments",
    "Hospitality terminals",
    "Digital commerce",
    "Travel services",
    "Public sector",
    "Mobility services",
]
MERCHANT_NAME_PREFIXES = [
    "Northstar Market",
    "Blue Harbor Cafe",
    "Atlas Mobility",
    "Greenline Retail",
    "Pixel Commerce",
    "Urban Travel Hub",
    "Nova Pharmacy",
    "Lumen Services",
]

INVALID_SOURCES = ["LEGACY", "MANUAL_IMPORT", "CSV_EXPORT", "UNKNOWN_SOURCE"]
INVALID_COUNTRIES = ["ZZ", "XX", "EU", "BENELUX"]
INVALID_ACTIVITY_DETAIL_STATUSES = ["Active-ish", "Dormant?", "Recently-ish"]
INVALID_MERCHANT_ACTIVITY_STATUSES = ["Maybe", "Paused", "Pending review"]
INVALID_ACTIVITY_TYPES = ["MAIL_ORDER", "QR_ONLY", "TERMINAL_UNKNOWN", "ECOM_ONLY"]
INVALID_CONTRACTING_METHODS = ["REMOTE_UNKNOWN", "API_ONBOARDING", "PARTNER_PORTAL"]
INVALID_CONTRACT_STATUSES = ["Frozen", "Suspended?", "Archived"]
INVALID_DATES = ["2026-99-99", "not-a-date", "31/31/2026", "1900-00-00"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PSQ customer-base data quality stress scenarios.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Extracted PSQ customer base CSV.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for scenario CSV files.")
    parser.add_argument(
        "--primary-stress-output",
        type=Path,
        default=DEFAULT_PRIMARY_STRESS,
        help="Main stress CSV used by the demo pipeline and deployed dashboards.",
    )
    parser.add_argument("--large-multiplier", type=int, default=5, help="Multiplier used for the large-volume case.")
    return parser.parse_args()


def load_source(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Source dataset was not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    return frame.fillna("")


def write_scenario(frame: pd.DataFrame, path: Path) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return {
        "name": path.stem,
        "path": path.as_posix(),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
    }


def cycled_values(length: int, values: list[str], offset: int = 0) -> list[str]:
    return [values[(index + offset) % len(values)] for index in range(length)]


def set_cycled(frame: pd.DataFrame, column: str, values: list[str], offset: int = 0) -> None:
    if column in frame.columns:
        frame.loc[:, column] = cycled_values(len(frame), values, offset)


def set_cycled_range(
    frame: pd.DataFrame,
    start: int,
    stop: int,
    column: str,
    values: list[str],
    offset: int = 0,
) -> None:
    if column not in frame.columns or frame.empty:
        return
    row_index = frame.index[start : min(stop + 1, len(frame))]
    frame.loc[row_index, column] = cycled_values(len(row_index), values, offset)


def set_blank_range(frame: pd.DataFrame, start: int, stop: int, column: str) -> None:
    set_cycled_range(frame, start, stop, column, [""])


def demo_dates(length: int, start_date: str, step_days: int, cycle_days: int) -> list[str]:
    base = pd.Timestamp(start_date)
    return [
        (base + pd.Timedelta(days=(index * step_days) % cycle_days)).strftime("%Y-%m-%d")
        for index in range(length)
    ]


def diversify_valid_values(frame: pd.DataFrame, *, offset: int = 0) -> pd.DataFrame:
    """Create realistic-looking fake customer rows before injecting quality defects."""
    result = frame.copy().reset_index(drop=True)
    if result.empty:
        return result

    set_cycled(result, "source", VALID_SOURCES, offset)
    set_cycled(result, "country", VALID_COUNTRIES, offset)
    set_cycled(result, "activity_detail_status", VALID_ACTIVITY_DETAIL_STATUSES, offset)
    set_cycled(result, "merchant_activity_status", VALID_MERCHANT_ACTIVITY_STATUSES, offset)
    set_cycled(result, "type_of_activity", VALID_ACTIVITY_TYPES, offset)
    set_cycled(result, "contracting_method", VALID_CONTRACTING_METHODS, offset)
    set_cycled(result, "contract_status", VALID_CONTRACT_STATUSES, offset)
    set_cycled(result, "legal_form", LEGAL_FORMS, offset)
    set_cycled(result, "mcc", MCC_CODES, offset)
    set_cycled(result, "contract_category_descriptions", CONTRACT_CATEGORIES, offset)

    if "last_trx_date" in result.columns:
        result["last_trx_date"] = demo_dates(len(result), "2025-01-03", 5, 520)
    if "vintage_date" in result.columns:
        result["vintage_date"] = demo_dates(len(result), "2021-02-01", 17, 1800)
    if "active_contracts" in result.columns:
        result["active_contracts"] = [str((index % 5) + 1) for index in range(len(result))]
    if "name" in result.columns:
        result["name"] = [
            f"{MERCHANT_NAME_PREFIXES[(index + offset) % len(MERCHANT_NAME_PREFIXES)]} {index + 1:05d}"
            for index in range(len(result))
        ]
    if "vat_number" in result.columns:
        result["vat_number"] = [f"VAT{800000000 + index:09d}" for index in range(len(result))]
    if "kvk_number" in result.columns:
        result["kvk_number"] = [f"{70000000 + index:08d}" for index in range(len(result))]
    if {"source", "id", "psq_entity_key"}.issubset(result.columns):
        result["psq_entity_key"] = result["source"].astype(str) + ":" + result["id"].astype(str)

    return result


def with_unique_suffix(frame: pd.DataFrame, suffix: str) -> pd.DataFrame:
    result = frame.copy()
    result["id"] = result["id"].astype(str) + suffix
    result["psq_entity_key"] = result["source"].astype(str) + ":" + result["id"].astype(str)
    return result


def control_case(source: pd.DataFrame) -> pd.DataFrame:
    return diversify_valid_values(source.head(min(len(source), 1000)), offset=1)


def missing_critical_case(source: pd.DataFrame) -> pd.DataFrame:
    frame = diversify_valid_values(source.head(min(len(source), 1500)), offset=2)
    set_blank_range(frame, 0, 24, "name")
    set_blank_range(frame, 25, 49, "country")
    set_blank_range(frame, 50, 74, "type_of_activity")
    set_blank_range(frame, 75, 99, "contracting_method")
    set_blank_range(frame, 100, 124, "contract_status")
    return frame


def duplicate_keys_case(source: pd.DataFrame) -> pd.DataFrame:
    frame = diversify_valid_values(source.head(min(len(source), 1500)), offset=3)
    duplicates = frame.head(75).copy()
    return pd.concat([frame, duplicates], ignore_index=True)


def invalid_domains_case(source: pd.DataFrame) -> pd.DataFrame:
    frame = diversify_valid_values(source.head(min(len(source), 1500)), offset=4)
    set_cycled_range(frame, 0, 24, "source", INVALID_SOURCES)
    set_cycled_range(frame, 25, 49, "country", INVALID_COUNTRIES)
    set_cycled_range(frame, 50, 74, "activity_detail_status", INVALID_ACTIVITY_DETAIL_STATUSES)
    set_cycled_range(frame, 75, 99, "merchant_activity_status", INVALID_MERCHANT_ACTIVITY_STATUSES)
    set_cycled_range(frame, 100, 124, "type_of_activity", INVALID_ACTIVITY_TYPES)
    set_cycled_range(frame, 125, 149, "contracting_method", INVALID_CONTRACTING_METHODS)
    set_cycled_range(frame, 150, 174, "contract_status", INVALID_CONTRACT_STATUSES)
    return frame


def invalid_dates_case(source: pd.DataFrame) -> pd.DataFrame:
    frame = diversify_valid_values(source.head(min(len(source), 1500)), offset=5)
    set_cycled_range(frame, 0, 39, "last_trx_date", INVALID_DATES)
    set_cycled_range(frame, 40, 79, "vintage_date", INVALID_DATES, offset=1)
    set_cycled_range(frame, 80, 119, "last_trx_date", INVALID_DATES, offset=2)
    set_cycled_range(frame, 120, 159, "vintage_date", INVALID_DATES, offset=3)
    return frame


def null_threshold_breach_case(source: pd.DataFrame) -> pd.DataFrame:
    frame = diversify_valid_values(source.head(min(len(source), 2000)), offset=6)
    set_blank_range(frame, 0, 1399, "mcc")
    set_blank_range(frame, 0, 1199, "vintage_date")
    set_blank_range(frame, 0, 1899, "legal_form")
    set_blank_range(frame, 0, 999, "last_trx_date")
    return frame


def large_volume_case(source: pd.DataFrame, multiplier: int) -> pd.DataFrame:
    source = diversify_valid_values(source, offset=7)
    chunks: list[pd.DataFrame] = []
    multiplier = max(multiplier, 1)
    for index in range(multiplier):
        chunks.append(with_unique_suffix(source.copy(), f"-B{index + 1:02d}"))
    return pd.concat(chunks, ignore_index=True)


def mixed_extreme_case(source: pd.DataFrame) -> pd.DataFrame:
    base = large_volume_case(source.head(min(len(source), 4000)).copy(), 3)
    set_blank_range(base, 0, 99, "name")
    set_cycled_range(base, 100, 199, "country", INVALID_COUNTRIES)
    set_cycled_range(base, 200, 299, "source", INVALID_SOURCES)
    set_cycled_range(base, 300, 399, "last_trx_date", INVALID_DATES)
    set_cycled_range(base, 400, 499, "vintage_date", INVALID_DATES, offset=1)
    set_cycled_range(base, 500, 649, "type_of_activity", INVALID_ACTIVITY_TYPES)
    set_cycled_range(base, 650, 799, "contracting_method", INVALID_CONTRACTING_METHODS)
    set_cycled_range(base, 800, 899, "contract_status", INVALID_CONTRACT_STATUSES)
    set_cycled_range(base, 900, 999, "activity_detail_status", INVALID_ACTIVITY_DETAIL_STATUSES)
    set_cycled_range(base, 1000, 1099, "merchant_activity_status", INVALID_MERCHANT_ACTIVITY_STATUSES)
    set_blank_range(base, 1100, 1499, "mcc")
    set_blank_range(base, 0, 10999, "active_contracts")
    set_blank_range(base, 0, 11899, "legal_form")
    set_blank_range(base, 1200, 5199, "vintage_date")
    base = pd.concat([base, base.head(100)], ignore_index=True)
    return base


def main() -> int:
    args = parse_args()
    source = load_source(args.source)
    scenarios = {
        "psq_control": control_case(source),
        "psq_missing_critical": missing_critical_case(source),
        "psq_duplicate_keys": duplicate_keys_case(source),
        "psq_invalid_domains": invalid_domains_case(source),
        "psq_invalid_dates": invalid_dates_case(source),
        "psq_null_threshold_breach": null_threshold_breach_case(source),
        "psq_large_volume": large_volume_case(source, args.large_multiplier),
        "psq_mixed_extreme": mixed_extreme_case(source),
    }

    manifest = {
        "source": args.source.as_posix(),
        "scenarios": [],
    }
    for name, frame in scenarios.items():
        manifest["scenarios"].append(write_scenario(frame, args.output_dir / f"{name}.csv"))

    args.primary_stress_output.parent.mkdir(parents=True, exist_ok=True)
    scenarios["psq_mixed_extreme"].to_csv(args.primary_stress_output, index=False)
    manifest["primary_stress_output"] = args.primary_stress_output.as_posix()

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Generated {len(scenarios)} PSQ stress scenarios in {args.output_dir}")
    print(f"Primary stress dataset: {args.primary_stress_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
