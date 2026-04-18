import pytest
from src.features.key_value import extract_key_value_pairs
from tests.features.conftest import make_block


def test_extracts_simple_kv():
    blocks = [make_block(clean_text="Hostname: server01.example.com")]
    result = extract_key_value_pairs(blocks)
    assert len(result) == 1
    r = result[0]
    assert r.feature_type == "key_value_pair"
    assert r.key == "Hostname"
    assert "server01.example.com" in r.value


def test_extracts_multiple_kv_from_one_block():
    text = "Name: Alice\nAge: 30\nRole: Engineer"
    blocks = [make_block(clean_text=text)]
    result = extract_key_value_pairs(blocks)
    assert len(result) == 3
    keys = {r.key for r in result}
    assert keys == {"Name", "Age", "Role"}


def test_value_format_is_key_colon_value():
    blocks = [make_block(clean_text="Version: 2.4.1")]
    r = extract_key_value_pairs(blocks)[0]
    assert r.value == "Version: 2.4.1"


def test_skips_rejected_blocks():
    blocks = [make_block(clean_text="Key: Value", gate_status="REJECT")]
    assert extract_key_value_pairs(blocks) == []


def test_skips_list_items():
    blocks = [make_block(block_type="list_item", clean_text="Key: Value")]
    assert extract_key_value_pairs(blocks) == []


def test_skips_key_without_letter():
    blocks = [make_block(clean_text="123: some value")]
    assert extract_key_value_pairs(blocks) == []


def test_key_max_length_respected():
    # Key > 80 chars should not match
    long_key = "K" * 81
    blocks = [make_block(clean_text=f"{long_key}: value")]
    assert extract_key_value_pairs(blocks) == []


def test_kv_in_heading_block():
    blocks = [make_block(
        block_type="heading_1",
        clean_text="Status: Active",
    )]
    result = extract_key_value_pairs(blocks)
    assert len(result) == 1
    assert result[0].key == "Status"
