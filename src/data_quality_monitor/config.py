from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class PipelineSettings:
    input_path: Path | None = None
    output_dir: Path = Path("reports/latest")


@dataclass(slots=True)
class DataQualityRules:
    required_columns: list[str] = field(default_factory=list)
    non_null_columns: list[str] = field(default_factory=list)
    unique_columns: list[str] = field(default_factory=list)
    positive_numeric_columns: list[str] = field(default_factory=list)
    date_columns: list[str] = field(default_factory=list)
    allowed_values: dict[str, list[str]] = field(default_factory=dict)
    null_thresholds: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class AppConfig:
    dataset: PipelineSettings
    checks: DataQualityRules


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        raw_config: dict[str, Any] = yaml.safe_load(handle) or {}

    dataset_config = raw_config.get("dataset", {})
    check_config = raw_config.get("checks", {})

    dataset = PipelineSettings(
        input_path=Path(dataset_config["input_path"]) if dataset_config.get("input_path") else None,
        output_dir=Path(dataset_config.get("output_dir", "reports/latest")),
    )

    checks = DataQualityRules(
        required_columns=list(check_config.get("required_columns", [])),
        non_null_columns=list(check_config.get("non_null_columns", [])),
        unique_columns=list(check_config.get("unique_columns", [])),
        positive_numeric_columns=list(check_config.get("positive_numeric_columns", [])),
        date_columns=list(check_config.get("date_columns", [])),
        allowed_values={
            key: [str(value) for value in values]
            for key, values in dict(check_config.get("allowed_values", {})).items()
        },
        null_thresholds={
            key: float(value) for key, value in dict(check_config.get("null_thresholds", {})).items()
        },
    )

    return AppConfig(dataset=dataset, checks=checks)

