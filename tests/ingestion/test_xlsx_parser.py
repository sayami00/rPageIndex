"""XLSX/CSV parser tests — builds in-memory spreadsheets with openpyxl/pandas."""
from __future__ import annotations

import pytest

pytest.importorskip("pandas")
pytest.importorskip("openpyxl")

import pandas as pd

from src.ingestion.xlsx_parser import XLSXParser


def _make_xlsx(tmp_path, sheets: dict) -> str:
    path = str(tmp_path / "test.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return path


def _make_csv(tmp_path, df: pd.DataFrame) -> str:
    path = str(tmp_path / "test.csv")
    df.to_csv(path, index=False)
    return path


def test_xlsx_sheets_as_pages(tmp_path):
    sheets = {
        "Sheet1": pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
        "Sheet2": pd.DataFrame({"X": [5, 6], "Y": [7, 8]}),
        "Sheet3": pd.DataFrame({"M": [9, 10], "N": [11, 12]}),
    }
    path = _make_xlsx(tmp_path, sheets)
    blocks = XLSXParser().parse(path)
    page_nums = sorted(b.page_number for b in blocks)
    assert page_nums == [1, 2, 3]


def test_xlsx_empty_sheet_skipped(tmp_path, caplog):
    import logging
    sheets = {
        "Data": pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
        "Empty": pd.DataFrame(),
    }
    path = _make_xlsx(tmp_path, sheets)
    with caplog.at_level(logging.WARNING):
        blocks = XLSXParser().parse(path)
    assert len(blocks) == 1
    assert blocks[0].page_number == 1
    assert any("empty" in r.message.lower() or "Empty" in r.message for r in caplog.records)


def test_csv_single_page(tmp_path):
    df = pd.DataFrame({"Name": ["Alice", "Bob"], "Score": ["90", "85"]})
    path = _make_csv(tmp_path, df)
    blocks = XLSXParser().parse(path)
    assert len(blocks) == 1
    assert blocks[0].page_number == 1
    assert blocks[0].source_format == "xlsx"


def test_xlsx_raw_headers_and_rows(tmp_path):
    df = pd.DataFrame({"Node": ["N1", "N2"], "IP": ["1.1.1.1", "2.2.2.2"]})
    path = _make_xlsx(tmp_path, {"Nodes": df})
    blocks = XLSXParser().parse(path)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.raw_headers == ["Node", "IP"]
    assert len(b.raw_rows) == 2
    assert b.raw_rows[0]["Node"] == "N1"
