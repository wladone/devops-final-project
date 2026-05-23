from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd


def load_dataset(
    input_path: str | Path,
    dtypes: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame.

    When ``dtypes`` is supplied (typically from ``rules.yml::dataset.dtypes``),
    it is forwarded to the underlying reader so columns are typed at parse
    time — closing the int+NaN promotes-to-float drift on CSV round-trips
    (issue #2).  Unknown columns in the map are tolerated by pandas.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input dataset was not found: {path}")

    dtype_map = dict(dtypes) if dtypes else None
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=dtype_map)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path, dtype=dtype_map)

    raise ValueError(
        f"Unsupported file format for {path.name}. Use CSV or Excel (.xlsx/.xls)."
    )


def load_from_sql_table(
    table_name: str,
    database_url: str | None = None,
    dtypes: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Load a full table from the SQL pipeline into a DataFrame.

    Used when the validator runs against the engine's *output* table
    (`analytics_psq_with_ricos_flag` by default) instead of a CSV — closing the
    loop so the same rule set proves quality on freshly-engineered data, not a
    static file. Lazy import keeps SQLAlchemy off the import path for CSV-only
    runs.
    """
    from sqlalchemy import select

    from data_quality_monitor.db import make_engine
    from data_quality_monitor.db_schema import ALL_TABLES

    if table_name not in ALL_TABLES:
        raise ValueError(
            f"Unknown table {table_name!r}. Known tables: {sorted(ALL_TABLES)}."
        )
    engine = make_engine(database_url)
    model = ALL_TABLES[table_name]
    with engine.connect() as conn:
        df = pd.read_sql(select(model), conn)

    if dtypes:
        for column, dtype in dtypes.items():
            if column in df.columns:
                df[column] = df[column].astype(dtype, errors="ignore")
    return df

