import pytest
from src.query.entity_extractor import extract_entities


def test_extract_ip():
    entities = extract_entities("show rules for 192.168.1.1")
    assert len(entities) == 1
    assert entities[0].entity_type == "ip"
    assert entities[0].value == "192.168.1.1"


def test_extract_hostname():
    entities = extract_entities("lookup dns.corp.internal")
    assert any(e.entity_type == "hostname" for e in entities)
    assert any(e.value == "dns.corp.internal" for e in entities)


def test_extract_version():
    entities = extract_entities("nginx v1.24.0 config")
    ver = [e for e in entities if e.entity_type == "version"]
    assert len(ver) >= 1
    assert "1.24.0" in ver[0].value or "v1.24.0" in ver[0].value


def test_extract_node():
    entities = extract_entities("web01 is down")
    node = [e for e in entities if e.entity_type == "node"]
    assert len(node) == 1
    assert node[0].value.lower() == "web01"


def test_no_overlap_ip_vs_hostname():
    # IP should not also match as hostname
    entities = extract_entities("10.0.0.1")
    types = {e.entity_type for e in entities}
    assert "ip" in types
    assert "hostname" not in types


def test_multiple_entities():
    entities = extract_entities("web01 at 192.168.1.10 running v2.0")
    types = {e.entity_type for e in entities}
    assert "ip" in types
    assert "version" in types
    assert "node" in types


def test_sorted_by_position():
    entities = extract_entities("192.168.1.1 then web01")
    starts = [e.start for e in entities]
    assert starts == sorted(starts)


def test_no_entities():
    assert extract_entities("show firewall config") == []


def test_node_db():
    entities = extract_entities("db01 replication lag")
    assert any(e.entity_type == "node" and "db01" in e.value.lower() for e in entities)


def test_node_srv():
    entities = extract_entities("srv02 memory usage high")
    assert any(e.entity_type == "node" for e in entities)


def test_version_without_v_prefix():
    entities = extract_entities("ubuntu 22.04 lts")
    ver = [e for e in entities if e.entity_type == "version"]
    assert len(ver) >= 1


def test_hostname_requires_dot():
    # bare "server" without dot should not match hostname
    entities = extract_entities("server status")
    assert not any(e.entity_type == "hostname" for e in entities)
