from __future__ import annotations

import pytest

from src.bm25.indexer import doc_count, open_or_create
from src.bm25.pipeline import IndexPipeline
from src.bm25.schemas import page_schema
from src.bm25.searcher import IndexSearcher
from tests.bm25.conftest import (
    make_feature_index,
    make_page_record,
    make_table,
    make_tree,
)


def _source_files(tmp_path, docs: dict[str, bytes]) -> dict[str, str]:
    paths = {}
    for doc_id, content in docs.items():
        p = tmp_path / f"{doc_id}.pdf"
        p.write_bytes(content)
        paths[doc_id] = str(p)
    return paths


@pytest.fixture
def pipeline(tmp_path):
    return IndexPipeline(index_root=str(tmp_path / "index"))


def _run(pipeline, tmp_path, doc_id="doc1", body="default body content"):
    sf = _source_files(tmp_path, {doc_id: b"PDF content " + body.encode()})
    records = [make_page_record(1, doc_id=doc_id, body_text=body)]
    trees = [make_tree(doc_id)]
    features = [make_feature_index(doc_id)]
    tables = [make_table(doc_id)]
    return pipeline.build(records, trees, features, tables, sf)


def test_build_returns_stats(pipeline, tmp_path):
    stats = _run(pipeline, tmp_path)
    assert "indices" in stats
    assert "documents" in stats


def test_build_indexes_pages(pipeline, tmp_path):
    _run(pipeline, tmp_path, body="unique authentication token")
    searcher = IndexSearcher(pipeline._root)
    results = searcher.search_pages("authentication")
    assert len(results) >= 1


def test_build_indexes_sections(pipeline, tmp_path):
    _run(pipeline, tmp_path)
    searcher = IndexSearcher(pipeline._root)
    results = searcher.search_sections("Introduction")
    assert len(results) >= 1


def test_build_indexes_features(pipeline, tmp_path):
    _run(pipeline, tmp_path)
    searcher = IndexSearcher(pipeline._root)
    results = searcher.search_features("192.168.1.1", exact=True)
    assert len(results) >= 1


def test_build_indexes_tables(pipeline, tmp_path):
    _run(pipeline, tmp_path)
    searcher = IndexSearcher(pipeline._root)
    results = searcher.search_tables("Host")
    assert len(results) >= 1


def test_incremental_skip_unchanged(pipeline, tmp_path):
    sf = _source_files(tmp_path, {"doc1": b"stable content"})
    records = [make_page_record(1, doc_id="doc1", body_text="stable content")]

    def do_build():
        return pipeline.build(records, [make_tree("doc1")], [make_feature_index("doc1")], [make_table("doc1")], sf)

    do_build()
    stats1 = do_build()  # second run — unchanged
    # document count unchanged — no re-index occurred, same number
    idx = open_or_create(pipeline._root, "page", page_schema)
    assert doc_count(idx) == 1  # still exactly one page


def test_incremental_reindex_on_change(pipeline, tmp_path):
    doc_file = tmp_path / "doc1.pdf"
    doc_file.write_bytes(b"original content")
    sf = {"doc1": str(doc_file)}

    records_v1 = [make_page_record(1, doc_id="doc1", body_text="original firewall config")]
    pipeline.build(records_v1, [make_tree("doc1")], [make_feature_index("doc1")], [], sf)

    # Modify file content → hash changes
    doc_file.write_bytes(b"completely new content after update")
    records_v2 = [make_page_record(1, doc_id="doc1", body_text="completely new deployment pipeline")]
    pipeline.build(records_v2, [make_tree("doc1")], [make_feature_index("doc1")], [], sf)

    searcher = IndexSearcher(pipeline._root)
    # New content findable
    assert len(searcher.search_pages("deployment")) >= 1
    # Old content gone
    assert len(searcher.search_pages("firewall")) == 0


def test_rebuild_force_reindexes(pipeline, tmp_path):
    sf = _source_files(tmp_path, {"doc1": b"content"})
    records = [make_page_record(1, doc_id="doc1", body_text="force rebuild test")]
    pipeline.build(records, [make_tree("doc1")], [], [], sf)
    # rebuild with same hash but force=True
    records2 = [make_page_record(1, doc_id="doc1", body_text="after forced rebuild")]
    pipeline.rebuild(records2, [make_tree("doc1")], [], [], sf)

    searcher = IndexSearcher(pipeline._root)
    assert len(searcher.search_pages("forced")) >= 1


def test_multi_doc_no_cross_contamination(pipeline, tmp_path):
    sf = _source_files(tmp_path, {
        "doc1": b"doc one content",
        "doc2": b"doc two content",
    })
    records = [
        make_page_record(1, doc_id="doc1", body_text="doc one unique alpha content"),
        make_page_record(1, doc_id="doc2", body_text="doc two unique beta content"),
    ]
    pipeline.build(records, [make_tree("doc1"), make_tree("doc2")], [], [], sf)

    searcher = IndexSearcher(pipeline._root)
    results = searcher.search_pages("alpha")
    assert all(r["doc_id"] == "doc1" for r in results)
