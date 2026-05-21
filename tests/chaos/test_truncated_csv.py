"""A truncated / partially-written CSV must surface a structured error,
never silently zero-row through to a misleadingly green report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_quality_monitor.data_loader import load_dataset
from data_quality_monitor.pipeline import run_pipeline

pytestmark = pytest.mark.chaos

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk" / "sparrowhawk_rules.yml"


HEADER = (
    "ringing_scheme,band_token,band_id,species_common,permit_code,bander_license,"
    "flyway_region,last_resight_date,migration_status,lifecycle_state,habitat_class,"
    "capture_method,morph_variant,taxon_code,first_banded_date,band_status,"
    "active_resights,observation_notes\n"
)


def test_truncated_row_raises_parser_error(tmp_path: Path) -> None:
    """A CSV truncated mid-row should raise a pandas ParserError (or a
    similarly explicit failure), not be silently accepted."""
    truncated = tmp_path / "truncated.csv"
    truncated.write_text(
        HEADER
        + 'Euring,Euring:RA-1,RA-1,"Goshawk',  # opening quote never closed
        encoding="utf-8",
    )
    with pytest.raises((pd.errors.ParserError, ValueError, pd.errors.EmptyDataError)):
        load_dataset(truncated)


def test_zero_byte_file_raises_explicit_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    with pytest.raises((pd.errors.EmptyDataError, ValueError)):
        load_dataset(empty)


def test_pipeline_propagates_truncation_failure(tmp_path: Path) -> None:
    """The pipeline must not silently produce a "100% quality" report on a
    truncated input — the error must surface to the caller."""
    truncated = tmp_path / "truncated.csv"
    truncated.write_text(HEADER + 'Euring,"unterminated', encoding="utf-8")
    with pytest.raises((pd.errors.ParserError, ValueError)):
        run_pipeline(input_path=truncated, rules_path=RULES, output_dir=tmp_path)
