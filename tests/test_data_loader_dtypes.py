"""Unit tests for the optional ``dtypes`` map on ``load_dataset`` (issue #2).

Goals:
- A column declared as ``str`` survives CSV round-trips without being
  coerced to int / float (which was the original drift).
- Absent ``dtypes`` keeps the previous, dtype-inferring behaviour for
  backward compatibility.
- Unknown columns in the map are tolerated by pandas (logged, not raised).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_quality_monitor.data_loader import load_dataset

pytestmark = pytest.mark.unit


CSV = (
    "band_id,active_resights\n"
    "0001,3\n"        # leading zero — only preserved as str
    "0002,\n"         # mixed with NaN
    "0003,7\n"
)


def test_dtype_str_preserves_leading_zeros(tmp_path: Path) -> None:
    src = tmp_path / "data.csv"
    src.write_text(CSV, encoding="utf-8")
    df = load_dataset(src, dtypes={"band_id": "str"})
    assert df["band_id"].tolist() == ["0001", "0002", "0003"]


def test_no_dtype_map_falls_back_to_inference(tmp_path: Path) -> None:
    """Default behaviour is preserved when ``dtypes`` is omitted."""
    src = tmp_path / "data.csv"
    src.write_text(CSV, encoding="utf-8")
    df = load_dataset(src)
    # pandas would infer integer (leading zeros lost) — confirms behaviour.
    assert df["band_id"].tolist() == [1, 2, 3]


def test_unknown_column_in_dtype_map_is_ignored(tmp_path: Path) -> None:
    """A column in the dtype map that isn't in the CSV must not crash."""
    src = tmp_path / "data.csv"
    src.write_text(CSV, encoding="utf-8")
    df = load_dataset(src, dtypes={"band_id": "str", "no_such_column": "str"})
    assert "band_id" in df.columns


def test_dtype_map_closes_csv_roundtrip_drift(tmp_path: Path) -> None:
    """The exact issue #2 scenario: with a dtype map, write -> read -> write
    is byte-identical on the first pass (no int->float promotion via NaN)."""
    src = tmp_path / "data.csv"
    src.write_text(CSV, encoding="utf-8")

    df1 = load_dataset(src, dtypes={"band_id": "str", "active_resights": "Int64"})
    rewrite = tmp_path / "rewrite.csv"
    df1.to_csv(rewrite, index=False, lineterminator="\n")
    df2 = load_dataset(rewrite, dtypes={"band_id": "str", "active_resights": "Int64"})

    pd.testing.assert_frame_equal(df1, df2)
