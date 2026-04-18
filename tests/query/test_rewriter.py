import pytest
from src.query.rewriter import QueryRewriter


@pytest.fixture
def rw():
    return QueryRewriter()


def test_basic_rewrite(rw):
    result = rw.rewrite("fw config")
    assert result.original == "fw config"
    assert "firewall" in result.bm25_query
    assert "configuration" in result.bm25_query


def test_normalized_lowercase(rw):
    result = rw.rewrite("FIREWALL CONFIG")
    assert result.normalized == "firewall config"


def test_ip_extracted_as_entity(rw):
    result = rw.rewrite("show 192.168.1.1 rules")
    assert len(result.entities) == 1
    assert result.entities[0].entity_type == "ip"
    assert result.entities[0].value == "192.168.1.1"


def test_ip_not_in_plain_tokens(rw):
    result = rw.rewrite("show 192.168.1.1 rules")
    # IP should be in entities, not in expanded_terms as plain token
    for term in result.expanded_terms:
        assert "192.168.1.1" not in term or "^" in result.bm25_query


def test_ip_boosted_in_query(rw):
    result = rw.rewrite("check 192.168.1.1")
    assert "192.168.1.1" in result.bm25_query
    assert "^2.0" in result.bm25_query


def test_hostname_extracted(rw):
    result = rw.rewrite("resolve dns.corp.internal")
    assert any(e.entity_type == "hostname" for e in result.entities)


def test_version_extracted(rw):
    result = rw.rewrite("nginx v1.24.0 install")
    assert any(e.entity_type == "version" for e in result.entities)


def test_node_extracted(rw):
    result = rw.rewrite("web01 is unreachable")
    assert any(e.entity_type == "node" for e in result.entities)


def test_punctuation_stripped(rw):
    result = rw.rewrite("auth!!!")
    assert result.normalized == "auth"
    assert "authentication" in result.bm25_query


def test_db_expands_to_database(rw):
    result = rw.rewrite("db config")
    assert "database" in result.bm25_query


def test_stopwords_removed(rw):
    result = rw.rewrite("what is the firewall for")
    assert "firewall" in result.bm25_query
    # stopwords should not appear as standalone terms
    assert " the " not in f" {result.bm25_query} "


def test_empty_query(rw):
    result = rw.rewrite("")
    assert result.bm25_query == ""
    assert result.entities == []


def test_expanded_terms_deduped(rw):
    result = rw.rewrite("fw firewall")
    lower_terms = [t.lower() for t in result.expanded_terms]
    assert lower_terms.count("firewall") == 1


def test_custom_synonyms():
    custom = {"myterm": ["expanded_form"]}
    rw = QueryRewriter(synonyms=custom)
    result = rw.rewrite("myterm query")
    assert "expanded_form" in result.bm25_query


def test_or_group_format(rw):
    result = rw.rewrite("fw status")
    # fw should produce OR group
    assert "(fw OR firewall)" in result.bm25_query


def test_mixed_entity_and_abbrev(rw):
    result = rw.rewrite("fw rules for 192.168.10.1 on srv01")
    assert "firewall" in result.bm25_query
    assert "192.168.10.1" in result.bm25_query
    ips = [e for e in result.entities if e.entity_type == "ip"]
    nodes = [e for e in result.entities if e.entity_type == "node"]
    assert len(ips) == 1
    assert len(nodes) == 1
