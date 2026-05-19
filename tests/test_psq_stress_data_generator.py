from pathlib import Path

import importlib.util

import pandas as pd


MODULE_PATH = Path("scripts/data/generate_psq_stress_data.py")


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_psq_stress_data", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_psq_frame() -> pd.DataFrame:
    row_count = 220
    return pd.DataFrame(
        {
            "source": ["Way4"] * row_count,
            "id": [f"200{i:03d}" for i in range(row_count)],
            "psq_entity_key": [f"Way4:200{i:03d}" for i in range(row_count)],
            "name": [f"Merchant {i}" for i in range(row_count)],
            "vat_number": [f"VAT{i:03d}" for i in range(row_count)],
            "kvk_number": [f"KVK{i:03d}" for i in range(row_count)],
            "country": ["NL"] * row_count,
            "last_trx_date": ["2025-01-01"] * row_count,
            "activity_detail_status": ["Active in last 12 months"] * row_count,
            "merchant_activity_status": ["Active"] * row_count,
            "type_of_activity": ["CP"] * row_count,
            "contracting_method": ["F2F"] * row_count,
            "contract_status": ["Active"] * row_count,
            "mcc": ["5411"] * row_count,
            "legal_form": ["BV"] * row_count,
            "active_contracts": ["1"] * row_count,
            "vintage_date": ["2021-01-01"] * row_count,
            "contract_category_descriptions": ["Retail payments"] * row_count,
        }
    )


def test_control_case_creates_varied_but_valid_demo_values() -> None:
    generator = load_generator_module()

    result = generator.control_case(base_psq_frame())

    assert len(result) == len(base_psq_frame())
    assert result["source"].nunique() > 1
    assert result["country"].nunique() > 1
    assert result["name"].str.contains("Merchant 0").sum() == 0
    assert result["psq_entity_key"].str.contains(":").all()


def test_mixed_extreme_case_injects_multiple_quality_failures() -> None:
    generator = load_generator_module()

    result = generator.mixed_extreme_case(base_psq_frame())

    assert "" in set(result["name"])
    assert any(value in generator.INVALID_COUNTRIES for value in result["country"])
    assert any(value in generator.INVALID_SOURCES for value in result["source"])
    assert result.duplicated(subset=["psq_entity_key"]).any()
