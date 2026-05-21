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

