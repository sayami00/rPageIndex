from src.query.builder import build_bm25_query
from src.query.models import ExtractedEntity


def test_single_term_no_synonyms():
    result = build_bm25_query([("firewall", [])], [])
    assert result == "firewall"


def test_or_group_with_synonyms():
    result = build_bm25_query([("fw", ["firewall"])], [])
    assert "fw" in result
    assert "firewall" in result
    assert "OR" in result


def test_ip_entity_boosted():
    ent = ExtractedEntity("192.168.1.1", "ip", 0, 11)
    result = build_bm25_query([], [ent])
    assert "192.168.1.1" in result
    assert "^2.0" in result


def test_hostname_entity_boosted():
    ent = ExtractedEntity("dns.corp.internal", "hostname", 0, 17)
    result = build_bm25_query([], [ent])
    assert "dns.corp.internal" in result
    assert "^2.0" in result


def test_version_entity_lower_boost():
    ent = ExtractedEntity("v1.24.0", "version", 0, 7)
    result = build_bm25_query([], [ent])
    assert "v1.24.0" in result
    assert "^1.5" in result


def test_node_entity_lower_boost():
    ent = ExtractedEntity("web01", "node", 0, 5)
    result = build_bm25_query([], [ent])
    assert "web01" in result
    assert "^1.5" in result


def test_combined_terms_and_entities():
    ent = ExtractedEntity("192.168.1.1", "ip", 0, 11)
    result = build_bm25_query([("fw", ["firewall"]), ("config", ["configuration"])], [ent])
    assert "firewall" in result
    assert "configuration" in result
    assert "192.168.1.1" in result
    assert "^2.0" in result


def test_empty_input():
    assert build_bm25_query([], []) == ""


def test_no_duplicate_terms_in_or_group():
    # "firewall" as original + "firewall" as expansion → should not appear twice
    result = build_bm25_query([("firewall", ["firewall"])], [])
    assert result.count("firewall") == 1


def test_custom_entity_boost():
    ent = ExtractedEntity("10.0.0.1", "ip", 0, 8)
    result = build_bm25_query([], [ent], entity_boost=5.0)
    assert "^5.0" in result
