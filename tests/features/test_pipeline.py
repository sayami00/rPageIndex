import pytest
from src.features.pipeline import FeaturePipeline
from tests.features.conftest import make_block


@pytest.fixture
def pipeline():
    return FeaturePipeline()


def _blocks():
    return [
        make_block(block_id="h1", block_type="heading_1",
                   clean_text="System Architecture", page_number=1),
        make_block(block_id="h2", block_type="heading_2",
                   clean_text="Network Configuration", page_number=2),
        make_block(block_id="b1", block_type="list_item",
                   clean_text="- Supports IPv4 and IPv6", page_number=2),
        make_block(block_id="b2", block_type="list_item",
                   clean_text="- Redundant power supply", page_number=2),
        make_block(block_id="p1", block_type="paragraph",
                   clean_text="Hostname: router01.example.com\nVersion: 3.2.1",
                   page_number=3),
        make_block(block_id="p2", block_type="paragraph",
                   clean_text="Connect to 10.0.0.1 for management access",
                   page_number=3),
        make_block(block_id="r1", block_type="paragraph",
                   clean_text="authentication required", gate_status="REJECT",
                   page_number=4),
    ]


def test_all_feature_types_present(pipeline):
    index = pipeline.run(_blocks())
    expected = {"heading", "bullet_item", "key_value_pair", "repeated_pattern", "named_entity"}
    assert set(index.keys()) == expected


def test_headings_extracted(pipeline):
    index = pipeline.run(_blocks())
    values = {r.value for r in index["heading"]}
    assert "System Architecture" in values
    assert "Network Configuration" in values


def test_bullet_items_extracted(pipeline):
    index = pipeline.run(_blocks())
    assert len(index["bullet_item"]) == 2


def test_kv_pairs_extracted(pipeline):
    index = pipeline.run(_blocks())
    keys = {r.key for r in index["key_value_pair"]}
    assert "Hostname" in keys
    assert "Version" in keys


def test_named_entities_extracted(pipeline):
    index = pipeline.run(_blocks())
    entities = index["named_entity"]
    ips = [r for r in entities if r.entity_subtype == "ip"]
    assert any("10.0.0.1" in r.value for r in ips)


def test_rejected_blocks_not_in_index(pipeline):
    index = pipeline.run(_blocks())
    all_records = [r for records in index.values() for r in records]
    reject_block_ids = {"r1"}
    assert not any(r.block_id in reject_block_ids for r in all_records)


def test_empty_input(pipeline):
    index = pipeline.run([])
    assert all(len(v) == 0 for v in index.values())


def test_query_heading_by_value(pipeline):
    index = pipeline.run(_blocks())
    hits = [r for r in index["heading"] if r.value == "System Architecture"]
    assert len(hits) == 1
    assert hits[0].block_id == "h1"


def test_query_kv_key_and_value_accessible(pipeline):
    index = pipeline.run(_blocks())
    hostname_records = [r for r in index["key_value_pair"] if r.key == "Hostname"]
    assert len(hostname_records) == 1
    assert "router01.example.com" in hostname_records[0].value
