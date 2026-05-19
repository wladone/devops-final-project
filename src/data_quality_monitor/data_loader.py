from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_dataset(input_path: str | Path) -> pd.DataFrame:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input dataset was not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path)

    raise ValueError(
        f"Unsupported file format for {path.name}. Use CSV or Excel (.xlsx/.xls)."
    )

