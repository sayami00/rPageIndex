from __future__ import annotations

import logging

from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.query import Term

from src.bm25.indexer import open_or_create
from src.bm25.schemas import feature_schema, page_schema, section_schema, table_schema

logger = logging.getLogger(__name__)


class IndexSearcher:
    """Read-only search interface over all four indices."""

    def __init__(self, index_root: str = ".index/"):
        self._root = index_root
        self._page_idx = open_or_create(index_root, "page", page_schema)
        self._section_idx = open_or_create(index_root, "section", section_schema)
        self._feature_idx = open_or_create(index_root, "feature", feature_schema)
        self._table_idx = open_or_create(index_root, "table", table_schema)

    def search_pages(self, query: str, limit: int = 10) -> list[dict]:
        fields = ["heading_text", "body_text", "table_text", "section_path"]
        return self._search(self._page_idx, fields, query, limit)

    def search_sections(self, query: str, limit: int = 10) -> list[dict]:
        fields = ["title", "summary"]
        return self._search(self._section_idx, fields, query, limit)

    def search_features(
        self,
        query: str,
        feature_type: str | None = None,
        exact: bool = False,
        limit: int = 10,
    ) -> list[dict]:
        with self._feature_idx.searcher() as s:
            if exact:
                # Exact match on raw value field — no parsing
                q = Term("feature_exact", query)
            else:
                parser = QueryParser("feature_text", self._feature_idx.schema)
                q = parser.parse(query)

            if feature_type:
                from whoosh.query import And
                type_q = Term("feature_type", feature_type)
                q = And([q, type_q])

            results = s.search(q, limit=limit)
            return [dict(r) for r in results]

    def search_tables(self, query: str, limit: int = 10) -> list[dict]:
        fields = ["headers_text", "search_rows_text"]
        return self._search(self._table_idx, fields, query, limit)

    # ── internal ───────────────────────────────────────────────────────────────

    @staticmethod
    def _search(index, fields: list[str], query: str, limit: int) -> list[dict]:
        if not query.strip():
            return []
        try:
            with index.searcher() as s:
                parser = MultifieldParser(fields, index.schema)
                q = parser.parse(query)
                results = s.search(q, limit=limit)
                return [dict(r) for r in results]
        except Exception as exc:
            logger.error("Search error: %s", exc)
            return []
