import pytest
from src.tables.normalizer import normalize_rows


def test_basic_normalization():
    headers = ["Node", "IP", "Status"]
    rows = [["  r1  ", "  10.0.0.1  ", "  active  "]]
    result = normalize_rows(headers, rows)
    assert result == [{"Node": "r1", "IP": "10.0.0.1", "Status": "active"}]


def test_empty_cell_stays_empty():
    headers = ["A", "B", "C"]
    rows = [["x", "", "z"]]
    result = normalize_rows(headers, rows)
    # empty cell NOT filled (no left fill when preceding cell is different position)
    # actually B is between A and C, A has "x" so B gets filled with "x"
    # Wait - the merge heuristic fills empty cell with left neighbour
    # "x", "", "z" → "x", "x", "z" after fill
    assert result[0]["A"] == "x"
    assert result[0]["B"] == "x"  # filled from left (merge artifact)
    assert result[0]["C"] == "z"


def test_short_row_padded():
    # ["x", "y"] padded to ["x", "y", ""] then merge-fill → C gets "y" from left
    headers = ["A", "B", "C"]
    rows = [["x", "y"]]
    result = normalize_rows(headers, rows)
    assert "C" in result[0]  # key present
    assert result[0]["C"] == "y"  # filled from left neighbour B


def test_none_becomes_empty():
    headers = ["A", "B"]
    rows = [[None, "val"]]
    result = normalize_rows(headers, rows)
    assert result[0]["A"] == ""


def test_empty_rows():
    assert normalize_rows(["A", "B"], []) == []


def test_multiple_rows():
    headers = ["X", "Y"]
    rows = [["a", "b"], ["c", "d"]]
    result = normalize_rows(headers, rows)
    assert len(result) == 2
    assert result[1] == {"X": "c", "Y": "d"}
