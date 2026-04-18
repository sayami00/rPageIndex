import pytest
from src.tables.serializer import serialize_row, serialize_table


def test_all_columns_appear_in_sentence():
    headers = ["Node", "Group", "IP1", "IP2"]
    row = {"Node": "r1", "Group": "A", "IP1": "10.0.0.1", "IP2": "10.0.0.2"}
    sentence = serialize_row(headers, row)
    for col in headers:
        assert col in sentence, f"Column '{col}' missing from: {sentence!r}"


def test_values_appear_verbatim():
    headers = ["IP", "Version"]
    row = {"IP": "192.168.1.100", "Version": "2.4.1"}
    sentence = serialize_row(headers, row)
    assert "192.168.1.100" in sentence
    assert "2.4.1" in sentence


def test_empty_cells_skipped():
    headers = ["A", "B", "C"]
    row = {"A": "val", "B": "", "C": "other"}
    sentence = serialize_row(headers, row)
    assert "B" not in sentence
    assert "A val" in sentence
    assert "C other" in sentence


def test_none_cells_skipped():
    headers = ["X", "Y"]
    row = {"X": None, "Y": "present"}
    sentence = serialize_row(headers, row)
    assert "X" not in sentence
    assert "Y present" in sentence


def test_boolean_true_column_name_only():
    headers = ["supports_vlan", "active"]
    row = {"supports_vlan": True, "active": True}
    sentence = serialize_row(headers, row)
    assert "supports_vlan" in sentence
    assert "active" in sentence
    assert "True" not in sentence


def test_boolean_false_omitted():
    headers = ["supports_vlan", "active"]
    row = {"supports_vlan": False, "active": True}
    sentence = serialize_row(headers, row)
    assert "supports_vlan" not in sentence
    assert "active" in sentence


def test_no_comma_separator():
    headers = ["A", "B", "C"]
    row = {"A": "1", "B": "2", "C": "3"}
    sentence = serialize_row(headers, row)
    assert "," not in sentence


def test_no_and_separator():
    headers = ["A", "B"]
    row = {"A": "x", "B": "y"}
    sentence = serialize_row(headers, row)
    assert " and " not in sentence


def test_serialize_table_one_sentence_per_row():
    headers = ["Node", "IP"]
    structured = [
        {"Node": "r1", "IP": "10.0.0.1"},
        {"Node": "r2", "IP": "10.0.0.2"},
    ]
    rows = serialize_table(headers, structured)
    assert len(rows) == 2
    assert "Node r1" in rows[0]
    assert "Node r2" in rows[1]


def test_serialize_table_empty():
    assert serialize_table(["A"], []) == []
