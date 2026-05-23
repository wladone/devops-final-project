"""SQLAlchemy 2.0 declarative models for the SQL pipeline.

Three logical layers, separated by table-name prefix:

  psq_*        — input customer base (data the engine reads)
  ricos_*      — input RICOS reference (data the engine reads)
  analytics_*  — engine output (data the engine writes)

Schema mirrors the notebook's source tables (gwgkunde4400 / presult4400 /
tbbo4400) where the names exist, and the notebook's output tables
(psq_with_ricos_flag, psq_with_ricos_rich, psq_match_summary).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Source layer (engine reads from these)
# ─────────────────────────────────────────────────────────────────────────────


class PsqCustomerBase(Base):
    """Unionized Way4 + PASS customer base.

    Equivalent to the notebook's `psq_customer_base_v8` DataFrame (cell 8),
    persisted as the engine's primary input table.
    """

    __tablename__ = "psq_customer_base"

    psq_entity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kvk_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    last_trx_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    activity_detail_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merchant_activity_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    type_of_activity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contracting_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mcc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vintage_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contract_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active_contracts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract_category_descriptions: Mapped[str | None] = mapped_column(Text, nullable=True)


class RicosMerchantLookup(Base):
    """RICOS gwgkunde4400 — merchant identity reference."""

    __tablename__ = "ricos_merchant_lookup"

    ricos_kundnr: Mapped[str] = mapped_column(String(32), primary_key=True)
    ricos_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ricos_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ricos_postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ricos_mcc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ricos_country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ricos_legal_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_kvk: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_duns_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_vat: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RicosRiskResult(Base):
    """RICOS presult4400 — risk & screening results."""

    __tablename__ = "ricos_risk_results"

    ricos_kundnr: Mapped[str] = mapped_column(String(32), primary_key=True)
    ricos_risk_score: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_risk_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ricos_risk_original: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_risk_manual: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_risk_inherited: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_screening_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_screening_pstatus: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_watchlist_hit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ricos_watchlist_list: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_embargo_hit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ricos_pep_hit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ricos_next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ricos_risk_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class RicosUboLink(Base):
    """RICOS tbbo4400 — UBO/SI relationship counts."""

    __tablename__ = "ricos_ubo_links"

    ricos_kundnr: Mapped[str] = mapped_column(String(32), primary_key=True)
    ricos_ubo_count: Mapped[int] = mapped_column(Integer, default=0)
    ricos_si_count: Mapped[int] = mapped_column(Integer, default=0)


# ─────────────────────────────────────────────────────────────────────────────
# Output layer (engine writes to these)
# ─────────────────────────────────────────────────────────────────────────────


class AnalyticsPsqWithRicosFlag(Base):
    """Mirrors notebook cell 17 output table
    `projects.riskdatascience.psq_aml_with_ricosflag`."""

    __tablename__ = "analytics_psq_with_ricos_flag"

    psq_entity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kvk_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    last_trx_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    activity_detail_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merchant_activity_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    type_of_activity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contracting_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mcc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vintage_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contract_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active_contracts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract_category_descriptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    in_ricos_flag: Mapped[str] = mapped_column(String(1), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalyticsPsqWithRicosRich(Base):
    """Mirrors notebook cell 19 output `psq_with_ricos_rich`. All 25 RICOS
    enrichment columns are nullable since unmatched merchants (in_ricos_flag=N)
    receive NULLs from the left join."""

    __tablename__ = "analytics_psq_with_ricos_rich"

    psq_entity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kvk_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    last_trx_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    activity_detail_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merchant_activity_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    type_of_activity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contracting_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mcc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    vintage_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contract_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active_contracts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract_category_descriptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    in_ricos_flag: Mapped[str] = mapped_column(String(1), index=True)
    ricos_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ricos_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ricos_postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ricos_mcc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ricos_country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ricos_legal_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_kvk: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_duns_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_vat: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_risk_score: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_risk_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ricos_risk_original: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_risk_manual: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_risk_inherited: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_screening_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_screening_pstatus: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_watchlist_hit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ricos_watchlist_list: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ricos_embargo_hit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ricos_pep_hit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ricos_next_review_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ricos_risk_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ricos_ubo_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ricos_si_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalyticsPsqMatchSummary(Base):
    """Mirrors notebook cell 15 — match rates broken down by source / in_ricos_flag."""

    __tablename__ = "analytics_psq_match_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    in_ricos_flag: Mapped[str] = mapped_column(String(1), index=True)
    merchants: Mapped[int] = mapped_column(Integer)
    active_merchants: Mapped[int] = mapped_column(Integer)
    pct_of_source: Mapped[float] = mapped_column(Float)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


SOURCE_TABLES = {
    "psq_customer_base": PsqCustomerBase,
    "ricos_merchant_lookup": RicosMerchantLookup,
    "ricos_risk_results": RicosRiskResult,
    "ricos_ubo_links": RicosUboLink,
}

OUTPUT_TABLES = {
    "analytics_psq_with_ricos_flag": AnalyticsPsqWithRicosFlag,
    "analytics_psq_with_ricos_rich": AnalyticsPsqWithRicosRich,
    "analytics_psq_match_summary": AnalyticsPsqMatchSummary,
}

ALL_TABLES = {**SOURCE_TABLES, **OUTPUT_TABLES}


def create_all(engine) -> None:
    """Create every table on the bound engine. Idempotent."""
    Base.metadata.create_all(engine)


def drop_all(engine) -> None:
    """Drop every table. Used by tests + the --reset flag on the orchestrator."""
    Base.metadata.drop_all(engine)
