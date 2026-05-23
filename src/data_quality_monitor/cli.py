from __future__ import annotations

import argparse
from pathlib import Path

from data_quality_monitor.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Data Quality Monitoring checks.")
    parser.add_argument(
        "--input",
        dest="input_path",
        default=None,
        help="Path to the CSV or Excel file that should be validated.",
    )
    parser.add_argument(
        "--rules",
        dest="rules_path",
        default="config/rules.yml",
        help="Path to the YAML rules configuration.",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Directory where the reports should be written.",
    )
    parser.add_argument(
        "--from-sql",
        dest="sql_table",
        default=None,
        help="Read input from a SQL table instead of a CSV (e.g. analytics_psq_with_ricos_flag).",
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=None,
        help="SQLAlchemy URL. Defaults to DQ_DATABASE_URL env or local SQLite file.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    outcome = run_pipeline(
        input_path=Path(args.input_path) if args.input_path else None,
        rules_path=Path(args.rules_path),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        sql_table=args.sql_table,
        database_url=args.database_url,
    )

    print("Data quality checks finished.")
    print(f"Rows processed: {outcome.summary['row_count']}")
    print(f"Checks passed: {outcome.summary['checks_passed']}")
    print(f"Checks failed: {outcome.summary['checks_failed']}")
    print(f"Quality score: {outcome.summary['quality_score']}%")
    print("Generated files:")
    for name, path in outcome.output_files.items():
        print(f"  - {name}: {path}")

    return 0

