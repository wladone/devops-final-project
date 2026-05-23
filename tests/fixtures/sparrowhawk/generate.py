"""Seeded generator for the Sparrowhawk fixture domain.

Produces 8 stress-scenario CSVs that mirror the row counts of
``data/stress/manifest.json`` but with column names and value vocabulary
that have no overlap with the production PSQ / Way4 merchant dataset.

Run ``python tests/fixtures/sparrowhawk/generate.py`` to (re)materialise the
CSVs under ``tests/fixtures/sparrowhawk/``.  Output is deterministic for a
given ``--seed`` (default: 20260521 — the date this scheme was introduced).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import date, timedelta
from pathlib import Path

COLUMNS: list[str] = [
    "ringing_scheme",
    "band_token",
    "band_id",
    "species_common",
    "permit_code",
    "bander_license",
    "flyway_region",
    "last_resight_date",
    "migration_status",
    "lifecycle_state",
    "habitat_class",
    "capture_method",
    "morph_variant",
    "taxon_code",
    "first_banded_date",
    "band_status",
    "active_resights",
    "observation_notes",
]

RINGING_SCHEMES = ["Euring", "NABU"]
FLYWAY_REGIONS = ["WEU", "EAA", "NAM", "EAF", "CAF", "BSM", "AWA", "NEO"]
MIGRATION_STATUSES = [
    "Resighted in last 12 months",
    "Lost contact >12 months",
    "Never resighted",
]
LIFECYCLE_STATES = ["Alive", "Recovered"]
HABITAT_CLASSES = ["WET", "TER", "WET+TER"]
CAPTURE_METHODS = ["MIST", "TRAP", "MIST+TRAP"]
MORPH_VARIANTS = ["pale", "dark", "intermediate"]
TAXON_CODES = ["ACCIPI", "FALCONI", "STRIGI", "PASSER", "CHARAD", "ANSERI"]
BAND_STATUSES = ["Active", "Replaced", "Recovered", "Issued", "Retired"]
SPECIES = [
    "Goshawk", "Kestrel", "Hobby", "Merlin", "Sparrowhawk", "Buzzard",
    "Marsh Harrier", "Peregrine", "Osprey", "Red Kite", "Honey Buzzard",
]
INVALID_FLYWAYS = ["WAK", "ZZZ", "Atlantic", "00", "north"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _band_id(rng: random.Random, index: int) -> str:
    return f"RA-{1_000_000 + index + rng.randint(0, 99):07d}"


def _date(rng: random.Random, start: date, end: date) -> str:
    span = (end - start).days
    return (start + timedelta(days=rng.randint(0, span))).isoformat()


def _row(rng: random.Random, index: int) -> dict[str, object]:
    scheme = rng.choice(RINGING_SCHEMES)
    band_id = _band_id(rng, index)
    return {
        "ringing_scheme": scheme,
        "band_token": f"{scheme}:{band_id}",
        "band_id": band_id,
        "species_common": rng.choice(SPECIES),
        "permit_code": f"EU-PERM-{rng.randint(1_000_000, 9_999_999)}" if rng.random() > 0.05 else "",
        "bander_license": f"BL-{rng.randint(10_000, 99_999)}" if rng.random() > 0.20 else "",
        "flyway_region": rng.choice(FLYWAY_REGIONS),
        "last_resight_date": _date(rng, date(2024, 1, 1), date(2026, 4, 30)) if rng.random() > 0.40 else "",
        "migration_status": rng.choice(MIGRATION_STATUSES),
        "lifecycle_state": rng.choice(LIFECYCLE_STATES),
        "habitat_class": rng.choice(HABITAT_CLASSES),
        "capture_method": rng.choice(CAPTURE_METHODS),
        "morph_variant": rng.choice(MORPH_VARIANTS) if rng.random() > 0.95 else "",
        "taxon_code": rng.choice(TAXON_CODES) if rng.random() > 0.40 else "",
        "first_banded_date": _date(rng, date(2015, 1, 1), date(2024, 12, 31)) if rng.random() > 0.30 else "",
        "band_status": rng.choice(BAND_STATUSES),
        "active_resights": rng.randint(0, 12) if rng.random() > 0.80 else "",
        "observation_notes": "",
    }


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_control(rng: random.Random, n: int = 1000) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i in range(n):
        row = _row(rng, i)
        # Control = no rule breaks; force populated critical fields.
        for col in ("permit_code", "bander_license"):
            if row[col] == "":
                row[col] = f"EU-PERM-{rng.randint(1_000_000, 9_999_999)}"
        rows.append(row)
    return rows


def scenario_missing_critical(rng: random.Random, n: int = 1500) -> list[dict[str, object]]:
    rows = [_row(rng, i) for i in range(n)]
    # Blank required non-null columns in 10% of rows.
    for row in rng.sample(rows, k=n // 10):
        row[rng.choice(["band_id", "species_common", "flyway_region", "band_status"])] = ""
    return rows


def scenario_duplicate_bands(rng: random.Random, n: int = 1575) -> list[dict[str, object]]:
    rows = [_row(rng, i) for i in range(n)]
    # Inject 75 exact-key duplicates of the first 75 rows.
    rows.extend(rows[:75])
    return rows[:n]


def scenario_invalid_flyways(rng: random.Random, n: int = 1500) -> list[dict[str, object]]:
    rows = [_row(rng, i) for i in range(n)]
    for row in rng.sample(rows, k=n // 8):
        row["flyway_region"] = rng.choice(INVALID_FLYWAYS)
    return rows


def scenario_invalid_dates(rng: random.Random, n: int = 1500) -> list[dict[str, object]]:
    rows = [_row(rng, i) for i in range(n)]
    bad = ["2025-02-31", "not-a-date", "31/12/2024", "2024-13-01", "0000-00-00"]
    for row in rng.sample(rows, k=n // 6):
        row[rng.choice(["last_resight_date", "first_banded_date"])] = rng.choice(bad)
    return rows


def scenario_null_breach(rng: random.Random, n: int = 2000) -> list[dict[str, object]]:
    rows = [_row(rng, i) for i in range(n)]
    # Push taxon_code null ratio well above its 0.50 threshold.
    for row in rng.sample(rows, k=int(n * 0.85)):
        row["taxon_code"] = ""
    # And blow past permit_code 0.01 threshold.
    for row in rng.sample(rows, k=int(n * 0.30)):
        row["permit_code"] = ""
    return rows


def scenario_large_volume(rng: random.Random, n: int = 60_500) -> list[dict[str, object]]:
    return [_row(rng, i) for i in range(n)]


def scenario_mixed_extreme(rng: random.Random, n: int = 12_100) -> list[dict[str, object]]:
    rows = [_row(rng, i) for i in range(n)]
    for row in rng.sample(rows, k=n // 20):
        row["flyway_region"] = rng.choice(INVALID_FLYWAYS)
    for row in rng.sample(rows, k=n // 25):
        row["last_resight_date"] = "2025-02-31"
    for row in rng.sample(rows, k=n // 30):
        row["band_id"] = ""
    rows.extend(rows[:50])  # a few duplicates
    return rows[:n]


SCENARIOS = {
    "rings_control.csv": (scenario_control, 1_000),
    "rings_missing_critical.csv": (scenario_missing_critical, 1_500),
    "rings_duplicate_bands.csv": (scenario_duplicate_bands, 1_575),
    "rings_invalid_flyways.csv": (scenario_invalid_flyways, 1_500),
    "rings_invalid_dates.csv": (scenario_invalid_dates, 1_500),
    "rings_null_breach.csv": (scenario_null_breach, 2_000),
    "rings_large_volume.csv": (scenario_large_volume, 60_500),
    "rings_mixed_extreme.csv": (scenario_mixed_extreme, 12_100),
}


def _stable_seed(base_seed: int, scenario_name: str) -> int:
    """Combine ``base_seed`` with the scenario name into a per-scenario RNG seed
    that is deterministic across Python processes.

    Using the built-in ``hash()`` is unsafe here: CPython's string hashing is
    randomised by ``PYTHONHASHSEED`` (default: random salt per interpreter
    startup), so ``hash("rings_control")`` returns a different integer on
    every run.  ``hashlib.sha256`` gives a stable bit pattern that the
    committed fixture CSVs and the golden baselines depend on.
    """
    digest = hashlib.sha256(scenario_name.encode("utf-8")).digest()
    # Top 32 bits are plenty of entropy for ``random.Random`` and keep the
    # seed printable when debugging.
    return base_seed ^ int.from_bytes(digest[:4], "big")


def build(output_dir: Path, seed: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, (fn, n) in SCENARIOS.items():
        rng = random.Random(_stable_seed(seed, name))
        rows = fn(rng, n)
        _write(output_dir / name, rows)
        counts[name] = len(rows)
    manifest = {
        "seed": seed,
        "columns": COLUMNS,
        "scenarios": [{"name": k, "rows": v} for k, v in counts.items()],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Sparrowhawk fixture CSVs.")
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    counts = build(args.output_dir, args.seed)
    for name, rows in counts.items():
        print(f"  {name}: {rows} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
