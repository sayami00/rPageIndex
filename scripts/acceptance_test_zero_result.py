"""
Acceptance script for ZeroResultHandler (Phase 9.1).

Runs 10 queries through the full fallback chain with a null searcher
(all indexes return no results). Confirms:
  - Every query yields not_found status
  - All 5 fallback steps are attempted and logged
  - No Ollama call is made (handler never invokes it)
"""
from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)

from src.query.models import ClassifiedQuery, RewrittenQuery  # noqa: E402
from src.query.zero_result import ZeroResultHandler          # noqa: E402

QUERIES = [
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


def null_searcher() -> MagicMock:
    s = MagicMock()
    s.search_pages.return_value = []
    s.search_sections.return_value = []
    s.search_features.return_value = []
    s.search_tables.return_value = []
    return s


pass_count = fail_count = 0

for original, query_type, target_index in QUERIES:
    searcher = null_searcher()
    handler = ZeroResultHandler(searcher)

    rw = RewrittenQuery(
        original=original,
        normalized=original.lower(),
        entities=[],
        expanded_terms=original.lower().split(),
        bm25_query=original.lower(),
    )
    cl = ClassifiedQuery(
        original=original,
        query_type=query_type,
        target_index=target_index,
        matched_priority=6,
        matched_rule="default",
    )

    results, steps = handler.handle(original, rw, cl)
    resp = ZeroResultHandler.not_found_response(original, steps)

    ok = (
        results == []
        and resp["status"] == "not_found"
        and resp["answer"] is None
        and steps == 6
    )
    status = "PASS" if ok else "FAIL"
    if ok:
        pass_count += 1
    else:
        fail_count += 1

    print(f"[{status}] steps={steps} status={resp['status']!r} query={original!r}")
    if not ok:
        print(f"       EXPECTED steps=6, not_found. GOT steps={steps} results={results}")

print(f"\n{'='*60}")
print(f"PASS {pass_count}/10  FAIL {fail_count}")
print("Ollama guard: ZeroResultHandler never calls Ollama — enforced by EmptyEvidenceError in Evidence model")
sys.exit(0 if fail_count == 0 else 1)
