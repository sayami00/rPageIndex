from __future__ import annotations

import pytest

from src.bm25.indexer import get_writer, open_or_create
from src.bm25.schemas import feature_schema, page_schema, section_schema, table_schema
from src.bm25.searcher import IndexSearcher
from src.bm25.writers import write_features, write_pages, write_sections, write_tables
from tests.bm25.conftest import (
    make_feature_index,
    make_page_record,
    make_table,
    make_tree,
)


@pytest.fixture
def populated_index(tmp_path):
    """Build all four indices with sample data; return (IndexSearcher, index_root)."""
    root = str(tmp_path)

    # page index
    pi = open_or_create(root, "page", page_schema)
    w = get_writer(pi)
    pages = [
        make_page_record(1, body_text="authentication tokens expire after timeout"),
        make_page_record(2, body_text="database connection pooling configuration"),
        make_page_record(3, heading_text="Network Security", body_text="firewall rules inspection"),
        make_page_record(4, body_text="memory allocation garbage collection"),
        make_page_record(5, body_text="deployment pipeline continuous integration"),
    ]
    write_pages(w, pages)
    w.commit()

    # section index
    si = open_or_create(root, "section", section_schema)
    w = get_writer(si)
    write_sections(w, make_tree("doc1", 10))
    w.commit()

    # feature index
    fi = open_or_create(root, "feature", feature_schema)
    w = get_writer(fi)
    write_features(w, make_feature_index("doc1"))
    w.commit()

    # table index
    ti = open_or_create(root, "table", table_schema)
    w = get_writer(ti)
    write_tables(w, [make_table("doc1")])
    w.commit()

    return IndexSearcher(root)


# ── page search ────────────────────────────────────────────────────────────────

def test_search_pages_finds_match(populated_index):
    results = populated_index.search_pages("authentication")
    assert len(results) >= 1
    assert any("authentication" in r.get("body_text", "").lower() for r in results)


def test_search_pages_stemming(populated_index):
    # "pool" should match "pooling" via StemmingAnalyzer
    results = populated_index.search_pages("pool")
    assert len(results) >= 1


def test_search_pages_heading_field(populated_index):
    results = populated_index.search_pages("Network Security")
    assert len(results) >= 1


def test_search_pages_no_match(populated_index):
    results = populated_index.search_pages("xyznonexistentterm12345")
    assert results == []


def test_search_pages_empty_query(populated_index):
    results = populated_index.search_pages("")
    assert results == []


# ── section search ─────────────────────────────────────────────────────────────

def test_search_sections_finds_title(populated_index):
    results = populated_index.search_sections("Introduction")
    assert len(results) >= 1
    assert any("Introduction" in r.get("title", "") for r in results)


def test_search_sections_finds_summary(populated_index):
    results = populated_index.search_sections("overview")
    assert len(results) >= 1


def test_search_sections_no_match(populated_index):
    results = populated_index.search_sections("xyznonexistentterm99999")
    assert results == []


# ── feature search ─────────────────────────────────────────────────────────────

def test_search_features_stemmed(populated_index):
    results = populated_index.search_features("Ubuntu")
    assert len(results) >= 1


def test_search_features_exact_ip(populated_index):
    results = populated_index.search_features("192.168.1.1", exact=True)
    assert len(results) >= 1
    assert results[0]["feature_exact"] == "192.168.1.1"


def test_search_features_exact_hostname(populated_index):
    results = populated_index.search_features("server01.example.com", exact=True)
    assert len(results) >= 1


def test_search_features_exact_nonexistent(populated_index):
    results = populated_index.search_features("10.0.0.99", exact=True)
    assert results == []


def test_search_features_by_type(populated_index):
    results = populated_index.search_features("192", feature_type="named_entity")
    # type filter applied — only named_entity results
    for r in results:
        assert r["feature_type"] == "named_entity"


def test_search_features_no_match(populated_index):
    results = populated_index.search_features("xyztermdoesnotexist")
    assert results == []


# ── table search ───────────────────────────────────────────────────────────────

def test_search_tables_headers(populated_index):
    results = populated_index.search_tables("Host")
    assert len(results) >= 1


def test_search_tables_rows(populated_index):
    results = populated_index.search_tables("active")
    assert len(results) >= 1


def test_search_tables_no_match(populated_index):
    results = populated_index.search_tables("xyztermdoesnotexist99")
    assert results == []
