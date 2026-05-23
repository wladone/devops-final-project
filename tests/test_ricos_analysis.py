"""Tests for the pandas port of the notebook's RICOS analysis layer."""

from __future__ import annotations

import pandas as pd
import pytest

from data_quality_monitor.ricos_analysis import (
    PASS_MATCH_RATE,
    RISK_DISTRIBUTION,
    WAY4_MATCH_RATE,
    attach_ricos_enrichment,
    attach_ricos_flag,
    build_ricos_join_key,
    compute_match_summary,
    generate_ricos_lookup,
    run_ricos_analysis,
)


@pytest.fixture
def mini_customer_base() -> pd.DataFrame:
    """Small synthetic customer base shaped like data/raw/psq_customer_base_v8.csv."""
    return pd.DataFrame(
        {
            "source": ["Way4"] * 6 + ["PASS"] * 4,
            "psq_entity_key": [f"KEY-{i:04d}" for i in range(10)],
            "id": [
                "2001190603", "2002700452", "2002554374",
                "2001277695", "2001514611", "2001539843",
                "835720", "873369", "834988", "835558",
            ],
            "name": [f"Merchant {i}" for i in range(10)],
            "vat_number": [f"NL{i:09d}B01" for i in range(10)],
            "kvk_number": [f"{i:08d}" for i in range(10)],
            "country": ["NL"] * 10,
            "mcc": ["5411"] * 10,
            "merchant_activity_status": ["Active"] * 7 + ["Inactive"] * 3,
        }
    )


def test_join_key_matches_notebook_formula() -> None:
    """The pandas port must produce the exact key the PySpark notebook produces.

    Reference: cell 15 of PSQ_customer_base_v8_ricos_analysis.ipynb —
        concat("P_M", lpad(regexp_replace(id, "[^0-9]", ""), 13, "0"))
    """
    ids = pd.Series(["2001190603", "835720", "WAY4;1234", "abc-5"])
    keys = build_ricos_join_key(ids)
    # Note: regex strips only non-digits, so the '4' inside 'WAY4' survives —
    # this matches what PySpark's regexp_replace('[^0-9]', '') would do too.
    assert keys.tolist() == [
        "P_M0002001190603",
        "P_M0000000835720",
        "P_M0000000041234",
        "P_M0000000000005",
    ]


def test_attach_ricos_flag_adds_only_one_column(mini_customer_base: pd.DataFrame) -> None:
    lookup = generate_ricos_lookup(mini_customer_base, seed=1)
    flagged = attach_ricos_flag(mini_customer_base, lookup)
    assert set(flagged.columns) == set(mini_customer_base.columns) | {"in_ricos_flag"}
    assert flagged["in_ricos_flag"].isin(["Y", "N"]).all()


def test_attach_ricos_enrichment_adds_all_ricos_columns(mini_customer_base: pd.DataFrame) -> None:
    lookup = generate_ricos_lookup(mini_customer_base, seed=1)
    rich = attach_ricos_enrichment(mini_customer_base, lookup)
    expected_ricos_cols = {
        "ricos_name", "ricos_street", "ricos_postal_code", "ricos_city",
        "ricos_mcc", "ricos_country", "ricos_legal_form", "ricos_kvk",
        "ricos_duns_id", "ricos_vat",
        "ricos_risk_score", "ricos_risk_label", "ricos_risk_original",
        "ricos_risk_manual", "ricos_risk_inherited",
        "ricos_screening_status", "ricos_screening_pstatus",
        "ricos_watchlist_hit_pct", "ricos_watchlist_list",
        "ricos_embargo_hit_pct", "ricos_pep_hit_pct",
        "ricos_next_review_date", "ricos_risk_comment",
        "ricos_ubo_count", "ricos_si_count",
        "in_ricos_flag",
    }
    assert expected_ricos_cols.issubset(set(rich.columns))


def test_unmatched_merchants_get_null_enrichment(mini_customer_base: pd.DataFrame) -> None:
    lookup = generate_ricos_lookup(mini_customer_base, seed=1)
    rich = attach_ricos_enrichment(mini_customer_base, lookup)
    unmatched = rich[rich["in_ricos_flag"] == "N"]
    assert unmatched["ricos_risk_score"].isna().all()
    assert unmatched["ricos_name"].isna().all()


def test_match_rates_within_tolerance_at_scale() -> None:
    """The notebook documents WAY4 ~71.4%, PASS ~35.3%. The deterministic bucketing
    should land within 2 percentage points on a full-size base."""
    base = pd.read_csv("data/raw/psq_customer_base_v8.csv")
    lookup = generate_ricos_lookup(base)
    flagged = attach_ricos_flag(base, lookup)
    summary = compute_match_summary(flagged)

    matched = summary[summary["in_ricos_flag"] == "Y"].set_index("source")["pct_of_source"]
    assert abs(matched["Way4"] - WAY4_MATCH_RATE * 100) < 2.0, matched.to_dict()
    assert abs(matched["PASS"] - PASS_MATCH_RATE * 100) < 2.0, matched.to_dict()


def test_run_is_deterministic(tmp_path) -> None:
    """Same seed + same input must produce byte-identical CSVs across runs."""
    first = run_ricos_analysis(
        input_path="data/raw/psq_customer_base_v8.csv",
        output_dir=tmp_path / "run1",
        seed=20260513,
    )
    second = run_ricos_analysis(
        input_path="data/raw/psq_customer_base_v8.csv",
        output_dir=tmp_path / "run2",
        seed=20260513,
    )
    pd.testing.assert_frame_equal(first.psq_with_ricos_flag, second.psq_with_ricos_flag)
    pd.testing.assert_frame_equal(first.psq_with_ricos_rich, second.psq_with_ricos_rich)
    pd.testing.assert_frame_equal(first.match_summary, second.match_summary)


def test_risk_distribution_approximates_configured_weights() -> None:
    base = pd.read_csv("data/raw/psq_customer_base_v8.csv")
    lookup = generate_ricos_lookup(base)
    observed = lookup["ricos_risk_score"].value_counts(normalize=True)
    for risk_class, expected in RISK_DISTRIBUTION.items():
        assert abs(observed[risk_class] - expected) < 0.03, observed.to_dict()
