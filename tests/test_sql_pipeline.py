"""End-to-end tests for the SQL-backed RICOS pipeline.

Uses an in-memory SQLite database per test so the suite stays fast and
hermetic — no shared state between cases, no file cleanup, identical results
on every CI machine.
"""

from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import create_engine, select, func

from data_quality_monitor.db_schema import (
    ALL_TABLES,
    AnalyticsPsqMatchSummary,
    AnalyticsPsqWithRicosFlag,
    AnalyticsPsqWithRicosRich,
    PsqCustomerBase,
    RicosMerchantLookup,
    RicosRiskResult,
    RicosUboLink,
    create_all,
)
from data_quality_monitor.sql_loader import load_all, load_customer_base, split_ricos_lookup
from data_quality_monitor.sql_pipeline import run_sql_pipeline
from data_quality_monitor.ricos_analysis import generate_ricos_lookup


@pytest.fixture
def memory_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def real_csv_path() -> str:
    return "data/raw/psq_customer_base_v8.csv"


def test_schema_creates_every_table(memory_engine) -> None:
    """create_all should provision all 7 logical tables."""
    inspector_result = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        memory_engine,
    )
    actual = set(inspector_result["name"].tolist())
    expected = set(ALL_TABLES.keys())
    assert expected.issubset(actual), f"Missing tables: {expected - actual}"


def test_load_customer_base_roundtrips_rows(memory_engine, real_csv_path) -> None:
    rows = load_customer_base(real_csv_path, memory_engine, replace=True)
    assert rows == 10_000

    with memory_engine.connect() as conn:
        total = int(conn.scalar(select(func.count()).select_from(PsqCustomerBase)))
        ways = int(
            conn.scalar(
                select(func.count())
                .select_from(PsqCustomerBase)
                .where(PsqCustomerBase.source == "Way4")
            )
        )
    assert total == 10_000
    assert ways == 8_039  # matches the source CSV breakdown


def test_ricos_split_produces_three_disjoint_tables() -> None:
    base = pd.read_csv("data/raw/psq_customer_base_v8.csv")
    combined = generate_ricos_lookup(base)
    splits = split_ricos_lookup(combined)

    assert set(splits.keys()) == {"merchant_lookup", "risk_results", "ubo_links"}
    # All three should be keyed on the same RICOS kundnr set
    merchant_keys = set(splits["merchant_lookup"]["ricos_kundnr"])
    risk_keys = set(splits["risk_results"]["ricos_kundnr"])
    ubo_keys = set(splits["ubo_links"]["ricos_kundnr"])
    assert merchant_keys == risk_keys == ubo_keys
    # Each table holds its own column subset (no leakage from one into another)
    assert "ricos_risk_score" not in splits["merchant_lookup"].columns
    assert "ricos_street" not in splits["risk_results"].columns
    assert "ricos_name" not in splits["ubo_links"].columns


def test_load_all_populates_every_source_table(memory_engine, real_csv_path) -> None:
    written = load_all(real_csv_path, memory_engine, replace=True)
    assert written["psq_customer_base"] == 10_000
    assert written["ricos_merchant_lookup"] > 6_000
    # All three RICOS tables share the same keyspace, so their row counts match.
    assert (
        written["ricos_merchant_lookup"]
        == written["ricos_risk_results"]
        == written["ricos_ubo_links"]
    )


def test_engine_writes_outputs_with_correct_row_counts(memory_engine, real_csv_path) -> None:
    load_all(real_csv_path, memory_engine)
    outcome = run_sql_pipeline(memory_engine)

    assert outcome.rows_with_flag == 10_000
    assert outcome.rows_with_rich == 10_000
    assert len(outcome.match_summary) == 4  # 2 sources × {Y, N}

    with memory_engine.connect() as conn:
        flag_rows = int(conn.scalar(select(func.count()).select_from(AnalyticsPsqWithRicosFlag)))
        rich_rows = int(conn.scalar(select(func.count()).select_from(AnalyticsPsqWithRicosRich)))
        summary_rows = int(conn.scalar(select(func.count()).select_from(AnalyticsPsqMatchSummary)))
    assert flag_rows == 10_000
    assert rich_rows == 10_000
    assert summary_rows == 4


def test_engine_preserves_match_rate_contract(memory_engine, real_csv_path) -> None:
    """Both CSV mode and SQL mode must hit the notebook's documented match rates
    on the real input — same join-key formula, same selection, same result."""
    load_all(real_csv_path, memory_engine)
    outcome = run_sql_pipeline(memory_engine)
    matched = outcome.match_summary[outcome.match_summary["in_ricos_flag"] == "Y"].set_index("source")
    assert abs(matched.loc["Way4", "pct_of_source"] - 71.4) < 2.0
    assert abs(matched.loc["PASS", "pct_of_source"] - 35.3) < 2.0


def test_unmatched_rows_have_null_ricos_columns(memory_engine, real_csv_path) -> None:
    load_all(real_csv_path, memory_engine)
    run_sql_pipeline(memory_engine)
    with memory_engine.connect() as conn:
        unmatched_with_score = int(
            conn.scalar(
                select(func.count())
                .select_from(AnalyticsPsqWithRicosRich)
                .where(
                    (AnalyticsPsqWithRicosRich.in_ricos_flag == "N")
                    & (AnalyticsPsqWithRicosRich.ricos_risk_score.is_not(None))
                )
            )
        )
    assert unmatched_with_score == 0


def test_replaces_existing_rows_on_reload(memory_engine, real_csv_path) -> None:
    """Loading twice should not duplicate rows — the loader replaces, not appends."""
    load_all(real_csv_path, memory_engine)
    load_all(real_csv_path, memory_engine)
    with memory_engine.connect() as conn:
        total = int(conn.scalar(select(func.count()).select_from(PsqCustomerBase)))
    assert total == 10_000


def test_pipeline_fails_clearly_when_sources_empty(memory_engine) -> None:
    """Running the engine without loaded sources should fail with a helpful message,
    not silently produce empty outputs."""
    with pytest.raises(RuntimeError, match="psq_customer_base is empty"):
        run_sql_pipeline(memory_engine)


# ─────────────────────────────────────────────────────────────────────────────
# Closing the loop: validator runs against the SQL output table
# ─────────────────────────────────────────────────────────────────────────────


def test_validator_reads_from_sql_output_table(memory_engine, real_csv_path, tmp_path) -> None:
    """The pipeline's validation step should be able to use the engine's output
    table (analytics_psq_with_ricos_flag) as its source — closing the loop."""
    import os
    from data_quality_monitor.pipeline import run_pipeline

    load_all(real_csv_path, memory_engine)
    run_sql_pipeline(memory_engine)

    # The validator opens its own connection — point it at the same DB.
    sqlite_url = "sqlite:///" + str((tmp_path / "validator_target.db").as_posix())
    # Easier path: copy the in-memory DB to a file the validator can reach.
    from data_quality_monitor.db import make_engine
    target_engine = make_engine(sqlite_url)

    # Re-run the loader + engine against the file DB so the validator has data.
    from data_quality_monitor.db_schema import create_all
    create_all(target_engine)
    load_all(real_csv_path, target_engine)
    run_sql_pipeline(target_engine)
    target_engine.dispose()

    outcome = run_pipeline(
        rules_path="config/rules.yml",
        output_dir=tmp_path / "validator_reports",
        sql_table="analytics_psq_with_ricos_flag",
        database_url=sqlite_url,
    )

    assert outcome.summary["row_count"] == 10_000
    assert outcome.summary["input_file"].startswith("sql://analytics_psq_with_ricos_flag")
    assert "quality_score" in outcome.summary
    # The enriched output should score higher than the raw stress CSV (~51%) —
    # we built it from the clean customer base. Sanity-check that.
    assert outcome.summary["quality_score"] > 80.0


def test_validator_errors_on_unknown_sql_table(tmp_path) -> None:
    """Asking for a table that's not in the schema should fail loudly."""
    from data_quality_monitor.pipeline import run_pipeline

    with pytest.raises(ValueError, match="Unknown table"):
        run_pipeline(
            rules_path="config/rules.yml",
            output_dir=tmp_path,
            sql_table="something_made_up",
            database_url="sqlite:///:memory:",
        )
