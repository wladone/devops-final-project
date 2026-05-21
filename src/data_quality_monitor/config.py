from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class PipelineSettings:
    input_path: Path | None = None
    output_dir: Path = Path("reports/latest")
    # Optional ``column -> dtype`` map honoured by ``data_loader.load_dataset``
    # when present (issue #2 — closes the int+NaN promotes-to-float drift on
    # CSV round-trip by letting the rules file declare expected types).
    dtypes: dict[str, str] = field(default_factory=dict)


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


# Exhaustive list of recognised keys.  Anything outside these sets in the
# rules YAML is treated as a typo and rejected (issue #6 — a typo like
# ``null_threshholds`` was previously accepted and silently ignored).
_TOP_LEVEL_KEYS = {"dataset", "checks"}
_DATASET_KEYS = {"input_path", "output_dir", "dtypes"}
_CHECK_KEYS = {
    "required_columns",
    "non_null_columns",
    "unique_columns",
    "positive_numeric_columns",
    "date_columns",
    "allowed_values",
    "null_thresholds",
}


class UnknownConfigKeyError(ValueError):
    """Raised when the rules YAML carries an unrecognised key (likely a typo)."""


def _reject_unknown(block_name: str, block: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(block.keys()) - allowed)
    if unknown:
        raise UnknownConfigKeyError(
            f"Unknown {block_name} key(s): {', '.join(unknown)}. "
            f"Allowed: {', '.join(sorted(allowed))}."
        )


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        raw_config: dict[str, Any] = yaml.safe_load(handle) or {}

    _reject_unknown("top-level", raw_config, _TOP_LEVEL_KEYS)

    dataset_config = raw_config.get("dataset", {}) or {}
    check_config = raw_config.get("checks", {}) or {}
    _reject_unknown("dataset", dataset_config, _DATASET_KEYS)
    _reject_unknown("checks", check_config, _CHECK_KEYS)

    dataset = PipelineSettings(
        input_path=Path(dataset_config["input_path"]) if dataset_config.get("input_path") else None,
        output_dir=Path(dataset_config.get("output_dir", "reports/latest")),
        dtypes={str(k): str(v) for k, v in dict(dataset_config.get("dtypes", {})).items()},
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

