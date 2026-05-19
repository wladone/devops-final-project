from pathlib import Path

import pandas as pd
import pytest

from data_quality_monitor.config import load_config
from data_quality_monitor.data_loader import load_dataset


def test_load_config_applies_defaults_and_type_coercion(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.yml"
    rules_path.write_text(
        "\n".join(
            [
                "dataset:",
                "  input_path: data/raw/customers.csv",
                "checks:",
                "  required_columns:",
                "    - customer_id",
                "  allowed_values:",
                "    country:",
                "      - NL",
                "      - 7",
                "  null_thresholds:",
                "    vat_number: '0.25'",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(rules_path)

    assert config.dataset.input_path == Path("data/raw/customers.csv")
    assert config.dataset.output_dir == Path("reports/latest")
    assert config.checks.required_columns == ["customer_id"]
    assert config.checks.allowed_values["country"] == ["NL", "7"]
    assert config.checks.null_thresholds["vat_number"] == 0.25


def test_load_config_handles_empty_yaml(tmp_path: Path) -> None:
    rules_path = tmp_path / "empty.yml"
    rules_path.write_text("", encoding="utf-8")

    config = load_config(rules_path)

    assert config.dataset.input_path is None
    assert config.dataset.output_dir == Path("reports/latest")
    assert config.checks.required_columns == []


def test_load_dataset_reads_csv_and_excel(tmp_path: Path) -> None:
    frame = pd.DataFrame({"customer_id": ["C-1", "C-2"], "amount": [10, 20]})
    csv_path = tmp_path / "customers.csv"
    xlsx_path = tmp_path / "customers.xlsx"
    frame.to_csv(csv_path, index=False)
    frame.to_excel(xlsx_path, index=False)

    csv_frame = load_dataset(csv_path)
    excel_frame = load_dataset(xlsx_path)

    assert csv_frame.to_dict("records") == frame.to_dict("records")
    assert excel_frame.to_dict("records") == frame.to_dict("records")


def test_load_dataset_rejects_missing_or_unsupported_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "missing.csv")

    text_path = tmp_path / "customers.txt"
    text_path.write_text("customer_id=C-1", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_dataset(text_path)
