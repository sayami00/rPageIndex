import pytest
from src.tables.header import parse_table_text, detect_header


def test_parse_pipe_delimited():
    text = "Node | IP | Status\nr1 | 10.0.0.1 | active\nr2 | 10.0.0.2 | inactive"
    rows = parse_table_text(text)
    assert len(rows) == 3
    assert rows[0] == ["Node", "IP", "Status"]
    assert rows[1] == ["r1", "10.0.0.1", "active"]


def test_parse_tab_delimited():
    text = "Node\tIP\tStatus\nr1\t10.0.0.1\tactive"
    rows = parse_table_text(text)
    assert len(rows) == 2
    assert rows[0] == ["Node", "IP", "Status"]


def test_parse_empty_text():
    rows = parse_table_text("")
    assert rows == []


def test_detect_header_first_row_labels():
    rows = [
        ["Node", "Group", "IP Address"],
        ["r1", "A", "10.0.0.1"],
        ["r2", "B", "10.0.0.2"],
    ]
    headers, data = detect_header(rows)
    assert headers == ["Node", "Group", "IP Address"]
    assert len(data) == 2


def test_detect_header_numeric_first_row_generates_synthetic():
    rows = [
        ["1", "2", "3"],
        ["10", "20", "30"],
    ]
    headers, data = detect_header(rows)
    assert all(h.startswith("col_") for h in headers)
    assert len(data) == 2


def test_detect_header_pads_short_rows():
    rows = [
        ["A", "B", "C"],
        ["x", "y"],  # short row
    ]
    headers, data = detect_header(rows)
    assert len(data[0]) == 3


def test_detect_header_empty_cells_get_synthetic_name():
    rows = [
        ["Name", "", "Value"],
        ["foo", "bar", "baz"],
    ]
    headers, data = detect_header(rows)
    assert headers[1] == "col_1"


def test_detect_header_empty_rows():
    headers, data = detect_header([])
    assert headers == []
    assert data == []
