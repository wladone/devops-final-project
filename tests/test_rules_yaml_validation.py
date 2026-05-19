from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from data_quality_monitor.config import AppConfig, load_config


def write_yaml(tmp_path: Path, content: str) -> Path:
    target = tmp_path / "rules.yml"
    target.write_text(content, encoding="utf-8")
    return target


def test_load_config_accepts_minimal_valid_rules(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        dataset:
          input_path: data/raw/dataset.csv
        checks:
          required_columns:
            - id
          non_null_columns: []
        """,
    )

    config = load_config(config_path)

    assert isinstance(config, AppConfig)
    assert config.dataset.input_path == Path("data/raw/dataset.csv")
    assert config.checks.required_columns == ["id"]


def test_load_config_tolerates_missing_top_level_sections(tmp_path: Path) -> None:
    config_path = write_yaml(tmp_path, "{}")

    config = load_config(config_path)

    assert config.dataset.input_path is None
    assert config.checks.required_columns == []
    assert config.checks.null_thresholds == {}


def test_load_config_raises_on_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yml"

    with pytest.raises(FileNotFoundError):
        load_config(missing)


def test_load_config_raises_on_malformed_yaml(tmp_path: Path) -> None:
    config_path = write_yaml(tmp_path, "dataset: : :\n  bogus")

    with pytest.raises(yaml.YAMLError):
        load_config(config_path)


def test_load_config_rejects_non_numeric_null_threshold(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        checks:
          null_thresholds:
            mcc: not_a_number
        """,
    )

    with pytest.raises(ValueError):
        load_config(config_path)


def test_load_config_coerces_allowed_values_to_strings(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        checks:
          allowed_values:
            country:
              - NL
              - 1
              - true
        """,
    )

    config = load_config(config_path)

    # All values become strings so downstream comparison is consistent.
    assert config.checks.allowed_values["country"] == ["NL", "1", "True"]


def test_load_config_handles_unicode_paths(tmp_path: Path) -> None:
    config_path = write_yaml(
        tmp_path,
        """
        dataset:
          input_path: data/raw/ăîșțé.csv
        """,
    )

    config = load_config(config_path)

    assert config.dataset.input_path == Path("data/raw/ăîșțé.csv")
