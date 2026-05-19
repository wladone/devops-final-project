from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_quality_monitor.data_loader import load_dataset


def test_load_dataset_handles_utf8_bom(tmp_path: Path) -> None:
    csv_path = tmp_path / "with_bom.csv"
    csv_path.write_bytes(b"\xef\xbb\xbfid,name\n1,Acme\n2,Beta\n")

    frame = load_dataset(csv_path)

    # Without BOM handling the first column name would start with ﻿.
    assert list(frame.columns) == ["id", "name"]
    assert len(frame) == 2


def test_load_dataset_handles_crlf_line_endings(tmp_path: Path) -> None:
    csv_path = tmp_path / "crlf.csv"
    csv_path.write_bytes(b"id,name\r\n1,Acme\r\n2,Beta\r\n")

    frame = load_dataset(csv_path)

    assert len(frame) == 2
    assert frame.iloc[1]["name"] == "Beta"


def test_load_dataset_returns_empty_frame_for_header_only_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "headers_only.csv"
    csv_path.write_text("id,name\n", encoding="utf-8")

    frame = load_dataset(csv_path)

    assert len(frame) == 0
    assert list(frame.columns) == ["id", "name"]


def test_load_dataset_handles_quoted_commas_inside_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "quotes.csv"
    csv_path.write_text(
        'id,name\n1,"Acme, Inc."\n2,"Beta ""Gamma"" Co"\n',
        encoding="utf-8",
    )

    frame = load_dataset(csv_path)

    assert frame.iloc[0]["name"] == "Acme, Inc."
    assert frame.iloc[1]["name"] == 'Beta "Gamma" Co'


def test_load_dataset_preserves_null_variants(tmp_path: Path) -> None:
    csv_path = tmp_path / "nulls.csv"
    csv_path.write_text("id,name\n1,\n2,NULL\n3,N/A\n4,nan\n", encoding="utf-8")

    frame = load_dataset(csv_path)

    # pandas treats "", "NULL", "N/A", and "nan" as NaN by default — this assertion
    # documents that behavior so a future loader change that strays from it shows up
    # as a test failure, not as a silent quality-report shift.
    assert frame["name"].isna().sum() == 4


def test_load_dataset_handles_single_row_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "one_row.csv"
    csv_path.write_text("id,name\n42,Solo\n", encoding="utf-8")

    frame = load_dataset(csv_path)

    assert len(frame) == 1
    assert frame.iloc[0]["id"] == 42


def test_load_dataset_raises_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.csv"

    with pytest.raises(FileNotFoundError):
        load_dataset(missing)


def test_load_dataset_rejects_unsupported_extension(tmp_path: Path) -> None:
    parquet_path = tmp_path / "data.parquet"
    parquet_path.write_bytes(b"not-really-parquet")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_dataset(parquet_path)


def test_load_dataset_handles_wide_row(tmp_path: Path) -> None:
    columns = [f"col_{idx}" for idx in range(120)]
    csv_path = tmp_path / "wide.csv"
    csv_path.write_text(
        ",".join(columns) + "\n" + ",".join(str(idx) for idx in range(120)) + "\n",
        encoding="utf-8",
    )

    frame = load_dataset(csv_path)

    assert frame.shape == (1, 120)


def test_load_dataset_reads_excel(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "tiny.xlsx"
    pd.DataFrame({"id": [1, 2], "name": ["Acme", "Beta"]}).to_excel(xlsx_path, index=False)

    frame = load_dataset(xlsx_path)

    assert list(frame.columns) == ["id", "name"]
    assert len(frame) == 2
