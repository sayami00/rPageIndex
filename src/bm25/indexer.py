from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import whoosh.index as wi
from whoosh.fields import Schema
from whoosh.index import FileIndex
from whoosh.writing import IndexWriter

logger = logging.getLogger(__name__)

_INDEX_DIRS = {
    "page": "page",
    "section": "section",
    "feature": "feature",
    "table": "table",
}


def open_or_create(index_root: str, index_name: str, schema_fn: Callable[[], Schema]) -> FileIndex:
    """Open existing Whoosh index or create it from schema_fn."""
    path = Path(index_root) / _INDEX_DIRS[index_name]
    path.mkdir(parents=True, exist_ok=True)
    if wi.exists_in(str(path)):
        return wi.open_dir(str(path))
    return wi.create_in(str(path), schema_fn())


def get_writer(index: FileIndex) -> IndexWriter:
    return index.writer()


def delete_by_doc(writer: IndexWriter, doc_id: str) -> None:
    """Remove all documents for a given doc_id from this index."""
    writer.delete_by_term("doc_id", doc_id)
    logger.debug("Deleted doc_id=%r from index", doc_id)


def doc_count(index: FileIndex) -> int:
    with index.searcher() as s:
        return s.doc_count()
