"""End-to-end SQL pipeline orchestrator.

Three stages:

  1. Create schema (idempotent).
  2. Load source tables from CSVs + synthetic RICOS generator.
  3. Run the engine: read sources, transform, write outputs.

Defaults to SQLite at `data/db/dq.db`. Override with `--database-url` or the
`DQ_DATABASE_URL` environment variable.

Typical use:
    python scripts/data/run_sql_pipeline.py --reset
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import select, func

from data_quality_monitor.db import make_engine
from data_quality_monitor.db_schema import (
    ALL_TABLES,
    AnalyticsPsqMatchSummary,
    AnalyticsPsqWithRicosFlag,
    AnalyticsPsqWithRicosRich,
    create_all,
    drop_all,
)
from data_quality_monitor.sql_loader import load_all
from data_quality_monitor.sql_pipeline import run_sql_pipeline


DEFAULT_INPUT = Path("data/raw/psq_customer_base_v8.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full SQL-backed RICOS pipeline.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="PSQ customer base CSV.")
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="SQLAlchemy URL. Defaults to DQ_DATABASE_URL env or local SQLite file.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop every table before reloading (default: append/replace per table).",
    )
    parser.add_argument("--seed", type=int, default=20260513, help="Deterministic RICOS seed.")
    return parser.parse_args()


def _count(engine, model) -> int:
    with engine.connect() as conn:
        return int(conn.scalar(select(func.count()).select_from(model)) or 0)


def main() -> int:
    args = parse_args()
    engine = make_engine(args.database_url)
    url_display = str(engine.url).replace("///", "/// ", 1)

    print("=" * 70)
    print("SQL-BACKED DATA QUALITY PIPELINE")
    print("=" * 70)
    print(f"Database:  {url_display}")
    print(f"Input CSV: {args.input}")
    print()

    if args.reset:
        print("[1/3] Dropping existing tables...")
        drop_all(engine)
    print("[1/3] Creating schema (idempotent)...")
    create_all(engine)
    for name in ALL_TABLES:
        print(f"      [ok] {name}")

    print()
    print("[2/3] Loading source tables from CSV + synthetic RICOS...")
    written = load_all(args.input, engine, seed=args.seed, replace=True)
    for table, rows in written.items():
        print(f"      [ok] {table:30s} {rows:>7,} rows")

    print()
    print("[3/3] Running engine: PSQ + RICOS sources -> analytics outputs...")
    outcome = run_sql_pipeline(engine)
    print(f"      [ok] Read   {outcome.rows_in_psq:>7,} from psq_customer_base")
    print(f"      [ok] Read   {outcome.rows_in_ricos:>7,} from ricos_* (joined)")
    print(f"      [ok] Wrote  {outcome.rows_with_flag:>7,} to analytics_psq_with_ricos_flag")
    print(f"      [ok] Wrote  {outcome.rows_with_rich:>7,} to analytics_psq_with_ricos_rich")
    print(f"      [ok] Wrote  {len(outcome.match_summary):>7,} to analytics_psq_match_summary")

    print()
    print("=" * 70)
    print("OUTPUT TABLE: analytics_psq_match_summary")
    print("=" * 70)
    print(outcome.match_summary.to_string(index=False))

    print()
    print("Sample SELECT from analytics_psq_with_ricos_rich:")
    print("-" * 70)
    sample_cols = [
        AnalyticsPsqWithRicosRich.source,
        AnalyticsPsqWithRicosRich.id,
        AnalyticsPsqWithRicosRich.name,
        AnalyticsPsqWithRicosRich.in_ricos_flag,
        AnalyticsPsqWithRicosRich.ricos_risk_score,
        AnalyticsPsqWithRicosRich.ricos_screening_status,
        AnalyticsPsqWithRicosRich.ricos_ubo_count,
    ]
    with engine.connect() as conn:
        sample = pd.read_sql(
            select(*sample_cols).where(AnalyticsPsqWithRicosRich.in_ricos_flag == "Y").limit(5),
            conn,
        )
    print(sample.to_string(index=False))

    in_ricos_total = _count(engine, AnalyticsPsqWithRicosFlag)
    with engine.connect() as conn:
        in_ricos_y = int(
            conn.scalar(
                select(func.count()).select_from(AnalyticsPsqWithRicosFlag).where(
                    AnalyticsPsqWithRicosFlag.in_ricos_flag == "Y"
                )
            )
            or 0
        )
    pct = 100 * in_ricos_y / max(in_ricos_total, 1)

    print()
    print(f"In-RICOS coverage: {in_ricos_y:,} / {in_ricos_total:,} ({pct:.1f}%)")
    print()
    print("Pipeline complete. Inspect the DB directly:")
    print(f"  sqlite3 data/db/dq.db '.tables'")
    print(f"  sqlite3 data/db/dq.db 'SELECT * FROM analytics_psq_match_summary;'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
