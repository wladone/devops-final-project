from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data_quality_monitor.config import load_config
from data_quality_monitor.data_loader import load_dataset, load_from_sql_table
from data_quality_monitor.report_generator import (
    build_report_dataframe,
    build_summary,
    write_reports,
)
from data_quality_monitor.validators import run_validation_checks


@dataclass(slots=True)
class PipelineOutcome:
    dataframe: pd.DataFrame
    report_frame: pd.DataFrame
    summary: dict[str, object]
    output_files: dict[str, Path]


def run_pipeline(
    input_path: str | Path | None = None,
    rules_path: str | Path = "config/rules.yml",
    output_dir: str | Path | None = None,
    sql_table: str | None = None,
    database_url: str | None = None,
) -> PipelineOutcome:
    """Validate a dataset against the configured rules.

    Source is either a CSV/XLSX file (`input_path`) or a SQL table
    (`sql_table` — e.g. `analytics_psq_with_ricos_flag`). When `sql_table` is
    given, `input_path` becomes a logical label embedded in the summary so
    reports stay traceable.
    """
    config = load_config(rules_path)
    resolved_output = Path(output_dir) if output_dir else config.dataset.output_dir

    if sql_table:
        dataframe = load_from_sql_table(sql_table, database_url=database_url, dtypes=config.dataset.dtypes or None)
        source_label = f"sql://{sql_table}"
    else:
        resolved_input = Path(input_path) if input_path else config.dataset.input_path
        if resolved_input is None:
            raise ValueError("No input file was provided and no default input_path exists in the rules file.")
        dataframe = load_dataset(resolved_input, dtypes=config.dataset.dtypes or None)
        source_label = resolved_input

    results = run_validation_checks(dataframe, config.checks)
    report_frame = build_report_dataframe(results)
    summary = build_summary(results, source_label, row_count=len(dataframe))  # type: ignore[arg-type]
    output_files = write_reports(report_frame, summary, resolved_output)

    return PipelineOutcome(
        dataframe=dataframe,
        report_frame=report_frame,
        summary=summary,
        output_files=output_files,
    )

