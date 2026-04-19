from __future__ import annotations

import logging

from src.bm25.searcher import IndexSearcher
from src.query.models import ClassifiedQuery, RewrittenQuery

logger = logging.getLogger(__name__)

_BROADER_INDEX: dict[str, str] = {
    "table_index":   "page_index",
    "section_index": "page_index",
    "feature_index": "page_index",
    "page_index":    "page_index",
}


class ZeroResultHandler:
    """
    Fallback chain invoked when an initial BM25 search returns zero results.

    Returns (results, steps_taken). Caller converts empty list to not_found response.
    Steps are numbered 2-5 to match the spec (step 1 = initial search, done by caller).
    """

    def __init__(self, searcher: IndexSearcher) -> None:
        self._searcher = searcher

    def handle(
        self,
        original_query: str,
        rewritten: RewrittenQuery,
        classified: ClassifiedQuery,
        limit: int = 10,
    ) -> tuple[list[dict], int]:
        target = classified.target_index

        # Step 2: relax — flat join of all expanded terms (no OR groups, no entity boosts)
        relaxed = " ".join(rewritten.expanded_terms) if rewritten.expanded_terms else rewritten.normalized
        results = self._search(target, relaxed, limit)
        if results:
            logger.info(
                "fallback step=2 rule=relax_synonyms index=%s query=%r returned=%d",
                target, relaxed, len(results),
            )
            return results, 2
        logger.info("fallback step=2 rule=relax_synonyms index=%s query=%r returned=0", target, relaxed)

        # Step 3: strip entity boost — plain normalized text on same index
        plain = rewritten.normalized
        results = self._search(target, plain, limit)
        if results:
            logger.info(
                "fallback step=3 rule=strip_entity_boost index=%s query=%r returned=%d",
                target, plain, len(results),
            )
            return results, 3
        logger.info("fallback step=3 rule=strip_entity_boost index=%s query=%r returned=0", target, plain)

        # Step 4: switch to broader index (table/section/feature → page_index)
        broader = _BROADER_INDEX[target]
        results = self._search(broader, plain, limit)
        if results:
            logger.info(
                "fallback step=4 rule=broader_index index=%s query=%r returned=%d",
                broader, plain, len(results),
            )
            return results, 4
        logger.info("fallback step=4 rule=broader_index index=%s query=%r returned=0", broader, plain)

        # Step 5: page_index with raw original query (no rewriting)
        results = self._search("page_index", original_query, limit)
        if results:
            logger.info(
                "fallback step=5 rule=raw_query index=page_index query=%r returned=%d",
                original_query, len(results),
            )
            return results, 5
        logger.info(
            "fallback step=5 rule=raw_query index=page_index query=%r returned=0",
            original_query,
        )

        # Step 6: stop
        logger.info(
            "fallback step=6 rule=not_found query=%r all_steps_exhausted", original_query
        )
        return [], 6

    @staticmethod
    def not_found_response(query: str, steps: int) -> dict:
        return {
            "answer": None,
            "status": "not_found",
            "message": "No relevant content found for this query.",
            "query_attempted": query,
            "fallback_steps_taken": steps,
        }

    # ── internal ───────────────────────────────────────────────────────────────

    def _search(self, index_name: str, query: str, limit: int) -> list[dict]:
        if not query.strip():
            return []
        if index_name == "page_index":
            return self._searcher.search_pages(query, limit)
        if index_name == "section_index":
            return self._searcher.search_sections(query, limit)
        if index_name == "feature_index":
            return self._searcher.search_features(query, limit=limit)
        if index_name == "table_index":
            return self._searcher.search_tables(query, limit)
        return []
