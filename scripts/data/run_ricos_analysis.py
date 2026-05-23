"""CLI wrapper for the RICOS analysis port.

Mirrors the analytical half of `notebooks/PSQ_customer_base_v8_ricos_analysis.ipynb`
but in pure pandas: feed the PSQ customer base CSV in, get real derived CSVs out.

Typical use:
    python scripts/data/run_ricos_analysis.py \
        --input data/raw/psq_customer_base_v8.csv \
        --output-dir data/processed/ricos
"""

from __future__ import annotations

import argparse
from pathlib import Path

from data_quality_monitor.ricos_analysis import run_ricos_analysis


DEFAULT_INPUT = Path("data/raw/psq_customer_base_v8.csv")
DEFAULT_OUTPUT_DIR = Path("data/processed/ricos")
DEFAULT_SEED = 20260513


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the RICOS analysis port on the PSQ customer base."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="PSQ customer base CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Where the derived RICOS CSVs land.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic generator seed.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outcome = run_ricos_analysis(input_path=args.input, output_dir=args.output_dir, seed=args.seed)

    flagged = outcome.psq_with_ricos_flag
    total = len(flagged)
    in_ricos = int((flagged["in_ricos_flag"] == "Y").sum())
    not_in_ricos = total - in_ricos

    print("RICOS analysis finished.")
    print(f"  Total merchants:   {total:,}")
    print(f"  In RICOS (Y):      {in_ricos:,} ({100*in_ricos/total:.1f}%)")
    print(f"  Not in RICOS (N):  {not_in_ricos:,} ({100*not_in_ricos/total:.1f}%)")
    print()
    print("Match rate by source:")
    print(outcome.match_summary.to_string(index=False))
    print()
    print("Generated files:")
    for name, path in outcome.output_files.items():
        print(f"  - {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
