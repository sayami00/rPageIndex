import pytest
from src.cleanup.table_cleanup import normalize_table_rows, normalize_headers


def test_strips_cell_whitespace():
    rows = [{"col1": "  hello  ", "col2": "  world  "}]
    result = normalize_table_rows(rows)
    assert result == [{"col1": "hello", "col2": "world"}]


def test_drops_fully_empty_rows():
    rows = [
        {"col1": "data", "col2": "more data"},
        {"col1": "", "col2": ""},
        {"col1": "last row", "col2": "value"},
    ]
    result = normalize_table_rows(rows)
    assert len(result) == 2
    assert result[0]["col1"] == "data"
    assert result[1]["col1"] == "last row"


def test_keeps_row_with_one_non_empty_cell():
    rows = [{"col1": "", "col2": "has value"}]
    result = normalize_table_rows(rows)
    assert len(result) == 1


def test_empty_rows_list():
    assert normalize_table_rows([]) == []


def test_normalize_headers():
    headers = ["  Name  ", "Value", "  Description  "]
    result = normalize_headers(headers)
    assert result == ["Name", "Value", "Description"]


def test_non_string_values_preserved():
    rows = [{"col1": 42, "col2": None}]
    result = normalize_table_rows(rows)
    assert result == [{"col1": 42, "col2": None}]
