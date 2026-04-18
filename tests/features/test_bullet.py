import pytest
from src.features.bullet import extract_bullet_items
from tests.features.conftest import make_block


def test_extracts_list_item():
    blocks = [make_block(block_type="list_item", clean_text="- First requirement")]
    result = extract_bullet_items(blocks)
    assert len(result) == 1
    assert result[0].feature_type == "bullet_item"
    assert result[0].value == "- First requirement"


def test_skips_non_list_blocks():
    blocks = [make_block(block_type="paragraph", clean_text="Not a bullet")]
    assert extract_bullet_items(blocks) == []


def test_skips_rejected():
    blocks = [make_block(block_type="list_item", gate_status="REJECT")]
    assert extract_bullet_items(blocks) == []


def test_multiple_bullets():
    blocks = [
        make_block(block_id=f"b{i}", block_type="list_item", clean_text=f"- Item {i}")
        for i in range(4)
    ]
    result = extract_bullet_items(blocks)
    assert len(result) == 4


def test_record_has_no_key_or_subtype():
    blocks = [make_block(block_type="list_item", clean_text="- Point")]
    r = extract_bullet_items(blocks)[0]
    assert r.key is None
    assert r.entity_subtype is None
    assert r.frequency is None
