import json

import pytest

from src.bm25.metadata import IndexMetadata


@pytest.fixture
def meta(tmp_path):
    return IndexMetadata(str(tmp_path))


def test_is_changed_unknown_doc(meta):
    assert meta.is_changed("doc_new", "abc123") is True


def test_record_and_unchanged(meta):
    meta.record_document("doc1", "f.pdf", "hash123")
    assert meta.is_changed("doc1", "hash123") is False


def test_record_and_changed(meta):
    meta.record_document("doc1", "f.pdf", "hash123")
    assert meta.is_changed("doc1", "newhash") is True


def test_save_and_reload(tmp_path):
    m1 = IndexMetadata(str(tmp_path))
    m1.record_document("doc1", "f.pdf", "abc")
    m1.record_index_build("page", 10, 100)
    m1.save()

    m2 = IndexMetadata(str(tmp_path))
    assert not m2.is_changed("doc1", "abc")
    stats = m2.index_stats("page")
    assert stats["document_count"] == 10
    assert stats["total_block_count"] == 100


def test_remove_document(meta):
    meta.record_document("doc1", "f.pdf", "h")
    meta.remove_document("doc1")
    assert meta.is_changed("doc1", "h") is True


def test_known_doc_ids(meta):
    meta.record_document("a", "a.pdf", "h1")
    meta.record_document("b", "b.pdf", "h2")
    assert meta.known_doc_ids() == {"a", "b"}


def test_all_stats_structure(meta):
    meta.record_index_build("page", 5)
    stats = meta.all_stats()
    assert "indices" in stats
    assert "documents" in stats
    assert "page" in stats["indices"]


def test_file_hash_is_deterministic(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello world")
    h1 = IndexMetadata.file_hash(str(f))
    h2 = IndexMetadata.file_hash(str(f))
    assert h1 == h2
    assert len(h1) == 16


def test_file_hash_changes_with_content(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"version 1")
    h1 = IndexMetadata.file_hash(str(f))
    f.write_bytes(b"version 2")
    h2 = IndexMetadata.file_hash(str(f))
    assert h1 != h2
