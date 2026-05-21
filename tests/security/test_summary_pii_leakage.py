"""Confirm ``summary.json`` does not leak row-level data.

The summary is shipped to dashboards, ticketing systems, and Jenkins logs;
it must contain *counts and check metadata only*, never row values from
the input dataset.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_quality_monitor.pipeline import run_pipeline

pytestmark = pytest.mark.security

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk" / "sparrowhawk_rules.yml"


# Tracer values we plant into the input — if any leak into summary.json,
# it means a validator is interpolating cell content into its message.
TRACER_BAND_ID = "RA-TRACER-9999999"
TRACER_SPECIES = "TRACER_SPECIES_UNIQUE_NAME"
TRACER_PERMIT = "EU-PERM-TRACER-1234567"


def _csv_with_tracers(path: Path) -> None:
    header = (
        "ringing_scheme,band_token,band_id,species_common,permit_code,bander_license,"
        "flyway_region,last_resight_date,migration_status,lifecycle_state,habitat_class,"
        "capture_method,morph_variant,taxon_code,first_banded_date,band_status,"
        "active_resights,observation_notes\n"
    )
    rows = [
        f"Euring,Euring:{TRACER_BAND_ID},{TRACER_BAND_ID},{TRACER_SPECIES},{TRACER_PERMIT},BL-1,WEU,,Never resighted,Alive,WET,MIST,,,,Active,,",
        f"NABU,NABU:RA-2,RA-2,Goshawk,EU-PERM-2,BL-2,WAK,,Never resighted,Alive,WET,MIST,,,,Active,,",  # invalid flyway
    ]
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def test_summary_contains_no_row_level_pii(tmp_path: Path) -> None:
    fixture = tmp_path / "tracer.csv"
    _csv_with_tracers(fixture)

    run_pipeline(input_path=fixture, rules_path=RULES, output_dir=tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    blob = json.dumps(summary)

    for tracer in (TRACER_BAND_ID, TRACER_SPECIES, TRACER_PERMIT):
        assert tracer not in blob, (
            f"Tracer {tracer!r} leaked into summary.json — a validator's "
            f"message field is interpolating user data."
        )
