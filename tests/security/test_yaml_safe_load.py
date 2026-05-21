"""Confirm ``load_config`` uses safe YAML loading.

If anyone ever swaps ``yaml.safe_load`` for ``yaml.load`` (or unsafe), a
malicious rules file could execute arbitrary Python on load.  This test
pins the contract by feeding a payload that *would* execute under
``yaml.load`` and asserting it is rejected.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from data_quality_monitor.config import load_config

pytestmark = pytest.mark.security

# `!!python/object/apply:os.system` is the canonical "this would run code"
# payload — safe_load rejects it with ConstructorError.
DANGEROUS_PAYLOAD = """\
dataset:
  input_path: data/raw/sample.csv
checks:
  required_columns: !!python/object/apply:os.system ["echo pwned"]
"""


def test_unsafe_yaml_is_rejected(tmp_path: Path) -> None:
    rules = tmp_path / "evil.yml"
    rules.write_text(DANGEROUS_PAYLOAD, encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_config(rules)


def test_safe_payload_still_loads(tmp_path: Path) -> None:
    rules = tmp_path / "ok.yml"
    rules.write_text(
        "dataset:\n  input_path: x.csv\nchecks:\n  required_columns: [a, b]\n",
        encoding="utf-8",
    )
    cfg = load_config(rules)
    assert cfg.checks.required_columns == ["a", "b"]
