import pytest
from src.features.named_entity import extract_named_entities
from tests.features.conftest import make_block


def test_extracts_ip_address():
    blocks = [make_block(clean_text="Connect to 192.168.1.100 on port 443")]
    result = extract_named_entities(blocks)
    ips = [r for r in result if r.entity_subtype == "ip"]
    assert len(ips) == 1
    assert ips[0].value == "192.168.1.100"


def test_extracts_version_string():
    blocks = [make_block(clean_text="Running firmware v2.4.1 on all nodes")]
    result = extract_named_entities(blocks)
    versions = [r for r in result if r.entity_subtype == "version"]
    assert any("2.4.1" in r.value for r in versions)


def test_extracts_hostname():
    blocks = [make_block(clean_text="Resolve api.example.com for DNS lookup")]
    result = extract_named_entities(blocks)
    hosts = [r for r in result if r.entity_subtype == "hostname"]
    assert any("api.example.com" in r.value for r in hosts)


def test_skips_rejected():
    blocks = [make_block(clean_text="10.0.0.1 is the gateway", gate_status="REJECT")]
    result = extract_named_entities(blocks)
    assert result == []


def test_deduplication_same_doc():
    # Same IP in two blocks of same doc → only first occurrence kept
    blocks = [
        make_block(block_id="b1", clean_text="Gateway 10.0.0.1 primary"),
        make_block(block_id="b2", clean_text="Gateway 10.0.0.1 backup"),
    ]
    result = extract_named_entities(blocks)
    ips = [r for r in result if r.entity_subtype == "ip" and r.value == "10.0.0.1"]
    assert len(ips) == 1
    assert ips[0].block_id == "b1"


def test_no_dedup_across_different_docs():
    blocks = [
        make_block(block_id="b1", doc_id="doc1", clean_text="Server 10.0.0.1"),
        make_block(block_id="b2", doc_id="doc2", clean_text="Server 10.0.0.1"),
    ]
    result = extract_named_entities(blocks)
    ips = [r for r in result if r.entity_subtype == "ip"]
    assert len(ips) == 2


def test_entity_subtype_set_correctly():
    blocks = [make_block(clean_text="Use 10.0.0.1 and v1.2.3 on node.example.com")]
    result = extract_named_entities(blocks)
    subtypes = {r.entity_subtype for r in result}
    assert "ip" in subtypes
    assert "version" in subtypes
    assert "hostname" in subtypes


def test_version_with_prerelease():
    blocks = [make_block(clean_text="Upgrade to v3.0.0-beta.1")]
    result = extract_named_entities(blocks)
    versions = [r for r in result if r.entity_subtype == "version"]
    assert any("3.0.0" in r.value for r in versions)


def test_empty_text():
    blocks = [make_block(clean_text="No entities here at all")]
    result = extract_named_entities(blocks)
    assert result == []
