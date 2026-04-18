from __future__ import annotations

import pytest
import whoosh.index as wi

from src.bm25.indexer import get_writer, open_or_create
from src.bm25.schemas import feature_schema, page_schema, section_schema, table_schema
from src.bm25.writers import resolve_section, write_features, write_pages, write_sections, write_tables
from tests.bm25.conftest import (
    make_feature_index,
    make_page_record,
    make_table,
    make_tree,
)


# ── resolve_section ────────────────────────────────────────────────────────────

def test_resolve_section_finds_deepest():
    tree = make_tree("doc1", total_pages=10)
    # page 2 is covered by both h1 (1-5) and h2 (2-3) → deepest = h2
    path, node_id = resolve_section(2, tree)
    assert "Background" in path
    assert "doc1::h2::b2" == node_id


def test_resolve_section_h1_only():
    tree = make_tree("doc1", total_pages=10)
    # page 4 covered by h1 (1-5) but not h2 (2-3)
    path, node_id = resolve_section(4, tree)
    assert "Introduction" in path
    assert node_id == "doc1::h1::b1"


def test_resolve_section_no_tree():
    path, node_id = resolve_section(3, None)
    assert path == ""
    assert node_id == ""


def test_resolve_section_out_of_range():
    tree = make_tree("doc1", total_pages=10)
    path, node_id = resolve_section(99, tree)
    assert path == ""
    assert node_id == ""


# ── write_pages ────────────────────────────────────────────────────────────────

@pytest.fixture
def page_index(tmp_path):
    return open_or_create(str(tmp_path), "page", page_schema)


def test_write_pages_count(page_index):
    recs = [make_page_record(i) for i in range(1, 6)]
    w = get_writer(page_index)
    count = write_pages(w, recs)
    w.commit()
    assert count == 5


def test_write_pages_section_path_populated(page_index):
    tree = make_tree("doc1", total_pages=10)
    recs = [make_page_record(2, doc_id="doc1")]
    w = get_writer(page_index)
    write_pages(w, recs, tree)
    w.commit()
    with page_index.searcher() as s:
        results = list(s.documents())
    assert len(results) == 1
    assert results[0]["section_path"] != ""


def test_write_pages_empty(page_index):
    w = get_writer(page_index)
    count = write_pages(w, [])
    w.commit()
    assert count == 0


# ── write_sections ─────────────────────────────────────────────────────────────

@pytest.fixture
def section_index(tmp_path):
    return open_or_create(str(tmp_path), "section", section_schema)


def test_write_sections_count(section_index):
    tree = make_tree("doc1", total_pages=10)
    w = get_writer(section_index)
    count = write_sections(w, tree)
    w.commit()
    assert count == 2  # h1 + h2 nodes, root excluded


def test_write_sections_fields_stored(section_index):
    tree = make_tree("doc1")
    w = get_writer(section_index)
    write_sections(w, tree)
    w.commit()
    with section_index.searcher() as s:
        docs = list(s.documents())
    ids = {d["section_id"] for d in docs}
    assert "doc1::h1::b1" in ids
    assert "doc1::h2::b2" in ids


# ── write_features ─────────────────────────────────────────────────────────────

@pytest.fixture
def feature_index(tmp_path):
    return open_or_create(str(tmp_path), "feature", feature_schema)


def test_write_features_count(feature_index):
    fi = make_feature_index("doc1")
    w = get_writer(feature_index)
    count = write_features(w, fi)
    w.commit()
    assert count == 3  # 2 named_entity + 1 key_value_pair


def test_write_features_exact_stored(feature_index):
    fi = make_feature_index("doc1")
    w = get_writer(feature_index)
    write_features(w, fi)
    w.commit()
    with feature_index.searcher() as s:
        docs = list(s.documents())
    exact_vals = {d["feature_exact"] for d in docs}
    assert "192.168.1.1" in exact_vals


# ── write_tables ───────────────────────────────────────────────────────────────

@pytest.fixture
def table_index(tmp_path):
    return open_or_create(str(tmp_path), "table", table_schema)


def test_write_tables_count(table_index):
    tables = [make_table("doc1"), make_table("doc2")]
    w = get_writer(table_index)
    count = write_tables(w, tables)
    w.commit()
    assert count == 2


def test_write_tables_source_pages_stored(table_index):
    tables = [make_table("doc1")]
    w = get_writer(table_index)
    write_tables(w, tables)
    w.commit()
    with table_index.searcher() as s:
        docs = list(s.documents())
    assert docs[0]["source_pages"] == "4 5"
