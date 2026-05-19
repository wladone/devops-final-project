from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from data_quality_monitor.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the data quality pipeline across stress scenario CSV files.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/stress"), help="Directory containing scenario CSVs.")
    parser.add_argument("--rules", type=Path, default=Path("config/rules.yml"), help="Rules YAML path.")
    parser.add_argument("--output-root", type=Path, default=Path("reports/stress"), help="Root directory for reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scenario_files = sorted(args.data_dir.glob("*.csv"))
    if not scenario_files:
        raise FileNotFoundError(f"No stress scenario CSV files found under {args.data_dir}")

    rows: list[dict[str, object]] = []
    for scenario_file in scenario_files:
        scenario_name = scenario_file.stem
        output_dir = args.output_root / scenario_name
        outcome = run_pipeline(input_path=scenario_file, rules_path=args.rules, output_dir=output_dir)
        rows.append(
            {
                "scenario": scenario_name,
                "input_file": scenario_file.as_posix(),
                "output_dir": output_dir.as_posix(),
                "row_count": outcome.summary["row_count"],
                "checks_total": outcome.summary["checks_total"],
                "checks_passed": outcome.summary["checks_passed"],
                "checks_failed": outcome.summary["checks_failed"],
                "quality_score": outcome.summary["quality_score"],
            }
        )

    args.output_root.mkdir(parents=True, exist_ok=True)
    summary_frame = pd.DataFrame(rows).sort_values(["quality_score", "scenario"], ascending=[True, True])
    summary_frame.to_csv(args.output_root / "stress_matrix_summary.csv", index=False)
    (args.output_root / "stress_matrix_summary.json").write_text(
        json.dumps(rows, indent=2),
        encoding="utf-8",
    )

    print("Stress matrix finished.")
    print(summary_frame.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
