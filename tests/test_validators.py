import pandas as pd

from data_quality_monitor.config import DataQualityRules
from data_quality_monitor.validators import run_validation_checks


def test_run_validation_checks_flags_expected_failures() -> None:
    dataframe = pd.DataFrame(
        {
            "invoice_id": ["INV-1", "INV-1"],
            "customer_id": ["C-1", None],
            "customer_segment": ["SMB", None],
            "invoice_date": ["2026-03-20", "invalid-date"],
            "amount": [100, -5],
            "currency": ["EUR", "GBP"],
        }
    )

    rules = DataQualityRules(
        required_columns=["invoice_id", "customer_id", "invoice_date", "amount", "currency"],
        non_null_columns=["customer_id", "invoice_date", "amount"],
        unique_columns=["invoice_id"],
        positive_numeric_columns=["amount"],
        date_columns=["invoice_date"],
        allowed_values={"currency": ["EUR", "USD", "RON"]},
        null_thresholds={"customer_segment": 0.10},
    )

    results = run_validation_checks(dataframe, rules)
    indexed = {(result.check_name, result.column_name): result for result in results}

    assert indexed[("required_columns_present", "dataset")].status == "PASS"
    assert indexed[("unique_key", "invoice_id")].status == "FAIL"
    assert indexed[("non_null", "customer_id")].status == "FAIL"
    assert indexed[("valid_date", "invoice_date")].status == "FAIL"
    assert indexed[("positive_numeric", "amount")].status == "FAIL"
    assert indexed[("allowed_values", "currency")].status == "FAIL"
    assert indexed[("null_threshold", "customer_segment")].status == "FAIL"


def test_run_validation_checks_passes_for_clean_data() -> None:
    dataframe = pd.DataFrame(
        {
            "invoice_id": ["INV-1", "INV-2"],
            "customer_id": ["C-1", "C-2"],
            "customer_segment": ["SMB", "Enterprise"],
            "invoice_date": ["2026-03-20", "2026-03-21"],
            "amount": [100, 250],
            "currency": ["EUR", "USD"],
        }
    )

    rules = DataQualityRules(
        required_columns=["invoice_id", "customer_id", "invoice_date", "amount", "currency"],
        non_null_columns=["customer_id", "invoice_date", "amount"],
        unique_columns=["invoice_id"],
        positive_numeric_columns=["amount"],
        date_columns=["invoice_date"],
        allowed_values={"currency": ["EUR", "USD", "RON"]},
        null_thresholds={"customer_segment": 0.50},
    )

    results = run_validation_checks(dataframe, rules)

    assert all(result.status == "PASS" for result in results)

