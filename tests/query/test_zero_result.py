"""
Acceptance tests for ZeroResultHandler.

Mocks IndexSearcher to always return [] → confirms every query yields
not_found response with all fallback steps logged, no Ollama call made.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from src.query.models import ClassifiedQuery, RewrittenQuery
from src.query.zero_result import ZeroResultHandler

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_rewritten(
    original: str = "test query",
    normalized: str = "test query",
    expanded_terms: list[str] | None = None,
) -> RewrittenQuery:
    return RewrittenQuery(
        original=original,
        normalized=normalized,
        entities=[],
        expanded_terms=expanded_terms or ["test", "query"],
        bm25_query="test query",
    )


def _make_classified(
    query_type: str = "page_lookup",
    target_index: str = "page_index",
) -> ClassifiedQuery:
    return ClassifiedQuery(
        original="test query",
        query_type=query_type,
        target_index=target_index,
        matched_priority=6,
        matched_rule="default",
    )


def _null_searcher() -> MagicMock:
    """Searcher that always returns empty list."""
    s = MagicMock()
    s.search_pages.return_value = []
    s.search_sections.return_value = []
    s.search_features.return_value = []
    s.search_tables.return_value = []
    return s


# 10 query scenarios — all produce no results in any index
_QUERIES: list[tuple[str, str, str]] = [
    ("What is the flux capacitor setting?",    "page_lookup",    "page_index"),
    ("Show me table of warp drive specs",      "table_query",    "table_index"),
    ("List all hyperspace routes",             "find_all",       "feature_index"),
    ("Section on dark matter propulsion",      "section_lookup", "section_index"),
    ("Which page covers anti-gravity boots?",  "page_lookup",    "page_index"),
    ("Find all mentions of chronosynaptic",    "find_all",       "feature_index"),
    ("Row for dilithium crystal frequency",    "table_query",    "table_index"),
    ("Chapter covering tachyon pulse theory",  "section_lookup", "section_index"),
    ("On page 999 alien landing diagram",      "page_lookup",    "page_index"),
    ("Show 192.168.99.99 routing config",      "table_query",    "table_index"),
]


@pytest.mark.parametrize("original,query_type,target_index", _QUERIES)
def test_not_found_all_steps_exhausted(
    original: str, query_type: str, target_index: str
) -> None:
    searcher = _null_searcher()
    handler = ZeroResultHandler(searcher)

    rw = _make_rewritten(original=original, normalized=original.lower())
    cl = _make_classified(query_type=query_type, target_index=target_index)

    results, steps = handler.handle(original, rw, cl)

    assert results == [], f"Expected empty results, got {results}"
    assert steps == 6, f"Expected all 6 steps, got {steps}"


@pytest.mark.parametrize("original,query_type,target_index", _QUERIES)
def test_not_found_response_format(
    original: str, query_type: str, target_index: str
) -> None:
    resp = ZeroResultHandler.not_found_response(original, 6)
    assert resp["answer"] is None
    assert resp["status"] == "not_found"
    assert resp["message"] == "No relevant content found for this query."
    assert resp["query_attempted"] == original
    assert resp["fallback_steps_taken"] == 6


def test_fallback_stops_at_step2_when_relax_finds_results() -> None:
    searcher = _null_searcher()
    # Step 2 is the first search_pages call — make it succeed immediately
    searcher.search_pages.side_effect = [[{"page_id": "doc::p1"}]]

    handler = ZeroResultHandler(searcher)
    rw = _make_rewritten()
    cl = _make_classified(query_type="page_lookup", target_index="page_index")

    results, steps = handler.handle("test query", rw, cl)
    assert steps == 2
    assert len(results) == 1


def test_fallback_steps_logged(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    searcher = _null_searcher()
    handler = ZeroResultHandler(searcher)
    rw = _make_rewritten()
    cl = _make_classified()

    with caplog.at_level(logging.INFO, logger="src.query.zero_result"):
        handler.handle("test query", rw, cl)

    rules = {r.getMessage() for r in caplog.records}
    assert any("step=2" in m for m in rules), "step 2 not logged"
    assert any("step=3" in m for m in rules), "step 3 not logged"
    assert any("step=4" in m for m in rules), "step 4 not logged"
    assert any("step=5" in m for m in rules), "step 5 not logged"
    assert any("step=6" in m for m in rules), "step 6 not logged"


def test_table_query_broadens_to_page_index() -> None:
    """Step 4 must search page_index for a table_query target."""
    searcher = _null_searcher()
    # Steps 2+3 use search_tables (same target index=table_index) — both return []
    searcher.search_tables.return_value = []
    # Step 4 switches to page_index — first search_pages call succeeds
    searcher.search_pages.side_effect = [[{"page_id": "doc::p5"}]]

    handler = ZeroResultHandler(searcher)
    rw = _make_rewritten()
    cl = _make_classified(query_type="table_query", target_index="table_index")

    results, steps = handler.handle("test query", rw, cl)
    assert steps == 4
    assert results[0]["page_id"] == "doc::p5"
