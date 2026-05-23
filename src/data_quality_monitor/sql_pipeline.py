"""SQL-backed analytics: read source tables, run the RICOS analysis, write
output tables.

This is the SQL-mode equivalent of `run_ricos_analysis` — same join-key
formula, same enrichment logic, but every input comes from a SELECT and every
output lands in an INSERT. The analytical core is the pure-pandas code in
`ricos_analysis.py`; this module is the I/O wrapper that makes it talk to a
database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import Engine, delete, select

from data_quality_monitor.db_schema import (
    AnalyticsPsqMatchSummary,
    AnalyticsPsqWithRicosFlag,
    AnalyticsPsqWithRicosRich,
    PsqCustomerBase,
    RicosMerchantLookup,
    RicosRiskResult,
    RicosUboLink,
)
from data_quality_monitor.ricos_analysis import (
    attach_ricos_enrichment,
    attach_ricos_flag,
    compute_match_summary,
)


@dataclass(slots=True)
class SqlPipelineOutcome:
    rows_in_psq: int
    rows_in_ricos: int
    rows_with_flag: int
    rows_with_rich: int
    in_ricos_count: int
    match_summary: pd.DataFrame


def _read_table(engine: Engine, model) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(select(model), conn)


def _truncate(engine: Engine, model) -> None:
    with engine.begin() as conn:
        conn.execute(delete(model))


def _join_ricos_sources(engine: Engine) -> pd.DataFrame:
    """Recombine the three RICOS source tables into the single lookup shape the
    analytics module expects. Inner-join on ricos_kundnr — every merchant in
    the lookup must have a risk row in this demo, mirroring the notebook's
    100% presult4400 coverage assumption."""
    merchant = _read_table(engine, RicosMerchantLookup)
    risk = _read_table(engine, RicosRiskResult)
    ubo = _read_table(engine, RicosUboLink)

    combined = merchant.merge(risk, on="ricos_kundnr", how="left")
    combined = combined.merge(ubo, on="ricos_kundnr", how="left")
    combined = combined.rename(columns={"ricos_kundnr": "ricos_join_key"})
    return combined


def run_sql_pipeline(engine: Engine) -> SqlPipelineOutcome:
    customer_base = _read_table(engine, PsqCustomerBase)
    if customer_base.empty:
        raise RuntimeError(
            "psq_customer_base is empty — run the loader before the pipeline."
        )

    ricos_lookup = _join_ricos_sources(engine)
    if ricos_lookup.empty:
        raise RuntimeError(
            "RICOS source tables are empty — run the loader before the pipeline."
        )

    flagged = attach_ricos_flag(customer_base, ricos_lookup)
    rich = attach_ricos_enrichment(customer_base, ricos_lookup)
    summary = compute_match_summary(flagged)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flagged_out = flagged.copy()
    flagged_out["generated_at"] = now
    rich_out = rich.copy()
    rich_out["generated_at"] = now

    if "ricos_next_review_date" in rich_out.columns:
        rich_out["ricos_next_review_date"] = rich_out["ricos_next_review_date"].astype("string")

    summary_out = summary.copy()
    summary_out["generated_at"] = now

    _truncate(engine, AnalyticsPsqWithRicosFlag)
    _truncate(engine, AnalyticsPsqWithRicosRich)
    _truncate(engine, AnalyticsPsqMatchSummary)

    flagged_out.to_sql(
        AnalyticsPsqWithRicosFlag.__tablename__,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    rich_out.to_sql(
        AnalyticsPsqWithRicosRich.__tablename__,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    summary_out.to_sql(
        AnalyticsPsqMatchSummary.__tablename__,
        engine,
        if_exists="append",
        index=False,
        method="multi",
    )

    return SqlPipelineOutcome(
        rows_in_psq=len(customer_base),
        rows_in_ricos=len(ricos_lookup),
        rows_with_flag=len(flagged_out),
        rows_with_rich=len(rich_out),
        in_ricos_count=int((flagged_out["in_ricos_flag"] == "Y").sum()),
        match_summary=summary,
    )
