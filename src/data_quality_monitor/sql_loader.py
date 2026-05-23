"""Populate the SQL source tables from the CSV fixtures.

This is the SQL equivalent of what the notebook's cells 4-10 do: build the
customer base and the three RICOS reference tables. Instead of reading from
Databricks, we read from the committed CSV (the offline export of cell 8) and
generate the RICOS reference data deterministically — same logic the CSV-mode
analytics already uses, just routed into three normalized tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import Engine, delete

from data_quality_monitor.db_schema import (
    PsqCustomerBase,
    RicosMerchantLookup,
    RicosRiskResult,
    RicosUboLink,
    create_all,
)
from data_quality_monitor.ricos_analysis import generate_ricos_lookup


CUSTOMER_BASE_COLUMNS = [
    "psq_entity_key", "source", "id", "name", "vat_number", "kvk_number",
    "country", "last_trx_date", "activity_detail_status", "merchant_activity_status",
    "type_of_activity", "contracting_method", "legal_form", "mcc",
    "vintage_date", "contract_status", "active_contracts",
    "contract_category_descriptions",
]

# The source CSV stores some Dutch names as double-encoded UTF-8 (e.g. "Coöperatieve"
# arrives on disk as the bytes for "CoÃ¶peratieve" re-encoded as UTF-8). Vectorized
# latin-1 -> utf-8 round-trip undoes the mojibake; rows that aren't mojibake are
# unaffected because ASCII survives latin-1 cleanly. We apply this only to free-form
# string columns where the mojibake is observed in practice.
_MOJIBAKE_COLUMNS = ("name", "contract_category_descriptions")


def _fix_one_cell(value: object) -> object:
    if value is None or pd.isna(value):
        return value
    text = str(value)
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Row contains characters outside latin-1 (e.g. real diacritics or
        # mojibake we can't undo cleanly). Leave it alone rather than mangle it.
        return text


def _fix_mojibake(df: pd.DataFrame) -> pd.DataFrame:
    for col in _MOJIBAKE_COLUMNS:
        if col not in df.columns:
            continue
        df[col] = df[col].apply(_fix_one_cell)
    return df

MERCHANT_LOOKUP_COLUMNS = [
    "ricos_kundnr", "ricos_name", "ricos_street", "ricos_postal_code",
    "ricos_city", "ricos_mcc", "ricos_country", "ricos_legal_form",
    "ricos_kvk", "ricos_duns_id", "ricos_vat",
]

RISK_RESULT_COLUMNS = [
    "ricos_kundnr", "ricos_risk_score", "ricos_risk_label", "ricos_risk_original",
    "ricos_risk_manual", "ricos_risk_inherited", "ricos_screening_status",
    "ricos_screening_pstatus", "ricos_watchlist_hit_pct", "ricos_watchlist_list",
    "ricos_embargo_hit_pct", "ricos_pep_hit_pct", "ricos_next_review_date",
    "ricos_risk_comment",
]

UBO_LINK_COLUMNS = ["ricos_kundnr", "ricos_ubo_count", "ricos_si_count"]


def _df_to_table(df: pd.DataFrame, engine: Engine, table_name: str, *, replace: bool = True) -> int:
    """Bulk-insert a DataFrame using pandas' to_sql. Returns rows written."""
    if replace:
        # We could TRUNCATE but pandas to_sql with if_exists="replace" recreates
        # the schema and we'd lose our column types. Use DELETE on the model.
        with engine.begin() as conn:
            conn.execute(delete_for(table_name))
    df.to_sql(table_name, engine, if_exists="append", index=False, method="multi", chunksize=1000)
    return len(df)


def delete_for(table_name: str):
    from data_quality_monitor.db_schema import ALL_TABLES

    model = ALL_TABLES[table_name]
    return delete(model)


def load_customer_base(csv_path: Path, engine: Engine, *, replace: bool = True) -> int:
    """Stream `psq_customer_base_v8.csv` into `psq_customer_base`."""
    df = pd.read_csv(csv_path)
    # Coerce active_contracts to nullable int so SQLite/Postgres accept NULLs cleanly.
    if "active_contracts" in df.columns:
        df["active_contracts"] = pd.to_numeric(df["active_contracts"], errors="coerce").astype("Int64")
    df = df[[c for c in CUSTOMER_BASE_COLUMNS if c in df.columns]]
    df = _fix_mojibake(df)
    return _df_to_table(df, engine, PsqCustomerBase.__tablename__, replace=replace)


def split_ricos_lookup(lookup_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split the combined synthetic lookup into the three notebook source tables
    (merchant_lookup, risk_results, ubo_links). Keyed by `ricos_kundnr`."""
    keyed = lookup_df.rename(columns={"ricos_join_key": "ricos_kundnr"}).copy()

    merchant = keyed[[c for c in MERCHANT_LOOKUP_COLUMNS if c in keyed.columns]].drop_duplicates("ricos_kundnr")
    risk = keyed[[c for c in RISK_RESULT_COLUMNS if c in keyed.columns]].drop_duplicates("ricos_kundnr")
    ubo = keyed[[c for c in UBO_LINK_COLUMNS if c in keyed.columns]].drop_duplicates("ricos_kundnr")

    # Cast numeric hit_pct columns to float so SQLite stores them as REAL.
    for col in ("ricos_watchlist_hit_pct", "ricos_embargo_hit_pct", "ricos_pep_hit_pct"):
        if col in risk.columns:
            risk[col] = pd.to_numeric(risk[col], errors="coerce")

    return {"merchant_lookup": merchant, "risk_results": risk, "ubo_links": ubo}


def load_ricos_sources(
    customer_base_df: pd.DataFrame,
    engine: Engine,
    *,
    seed: int = 20260513,
    replace: bool = True,
) -> dict[str, int]:
    """Generate the synthetic RICOS reference and split it into three tables."""
    combined = generate_ricos_lookup(customer_base_df, seed=seed)
    splits = split_ricos_lookup(combined)

    written = {
        "ricos_merchant_lookup": _df_to_table(
            splits["merchant_lookup"], engine, RicosMerchantLookup.__tablename__, replace=replace
        ),
        "ricos_risk_results": _df_to_table(
            splits["risk_results"], engine, RicosRiskResult.__tablename__, replace=replace
        ),
        "ricos_ubo_links": _df_to_table(
            splits["ubo_links"], engine, RicosUboLink.__tablename__, replace=replace
        ),
    }
    return written


def load_all(csv_path: Path, engine: Engine, *, seed: int = 20260513, replace: bool = True) -> dict[str, int]:
    """One-call loader: ensure schema exists, then populate every source table."""
    create_all(engine)
    customer_rows = load_customer_base(csv_path, engine, replace=replace)
    customer_df = _fix_mojibake(pd.read_csv(csv_path))
    ricos_counts = load_ricos_sources(customer_df, engine, seed=seed, replace=replace)
    return {"psq_customer_base": customer_rows, **ricos_counts}
