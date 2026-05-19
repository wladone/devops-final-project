from pathlib import Path

import pandas as pd

from data_quality_monitor.pipeline import run_pipeline


def test_run_pipeline_writes_reports(tmp_path: Path) -> None:
    input_path = tmp_path / "orders.csv"
    dataframe = pd.DataFrame(
        {
            "invoice_id": ["INV-1", "INV-2"],
            "customer_id": ["C-1", "C-2"],
            "customer_segment": ["SMB", "Enterprise"],
            "invoice_date": ["2026-03-20", "2026-03-21"],
            "amount": [100, 250],
            "currency": ["EUR", "USD"],
        }
    )
    dataframe.to_csv(input_path, index=False)

    rules_path = tmp_path / "rules.yml"
    rules_path.write_text(
        "\n".join(
            [
                "dataset:",
                f"  input_path: {input_path.as_posix()}",
                "  output_dir: reports/test-output",
                "",
                "checks:",
                "  required_columns:",
                "    - invoice_id",
                "    - customer_id",
                "    - invoice_date",
                "    - amount",
                "    - currency",
                "  non_null_columns:",
                "    - customer_id",
                "    - invoice_date",
                "    - amount",
                "  unique_columns:",
                "    - invoice_id",
                "  positive_numeric_columns:",
                "    - amount",
                "  date_columns:",
                "    - invoice_date",
                "  allowed_values:",
                "    currency:",
                "      - EUR",
                "      - USD",
                "  null_thresholds:",
                "    customer_segment: 0.50",
            ]
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "reports"
    outcome = run_pipeline(input_path=input_path, rules_path=rules_path, output_dir=output_dir)

    assert outcome.summary["checks_failed"] == 0
    assert (output_dir / "quality_report.csv").exists()
    assert (output_dir / "quality_report.xlsx").exists()
    assert (output_dir / "summary.json").exists()

