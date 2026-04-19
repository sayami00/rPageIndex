"""
30-query acceptance test for QueryRouter.
Each case: (query, expected_query_type, expected_target_index, expected_priority)
"""
from __future__ import annotations

import pytest

from src.query.router import QueryRouter

router = QueryRouter()

# fmt: off
CASES: list[tuple[str, str, str, int]] = [
    # --- Priority 1: IP address ---
    ("What is 192.168.1.1 configured for?",          "table_query",    "table_index",   1),
    ("Show me 10.0.0.5 settings",                    "table_query",    "table_index",   1),
    ("Which host uses 172.16.254.1",                 "table_query",    "table_index",   1),

    # --- Priority 2: table keywords ---
    ("Show the table of error codes",                "table_query",    "table_index",   2),
    ("What is in row 3 of the config",               "table_query",    "table_index",   2),
    ("Which column holds the port numbers",          "table_query",    "table_index",   2),
    ("Find the cell with value timeout",             "table_query",    "table_index",   2),
    ("Give me the routing table",                    "table_query",    "table_index",   2),

    # --- Priority 3: find_all keywords ---
    ("List all error messages",                      "find_all",       "feature_index", 3),
    ("Find all instances of timeout",                "find_all",       "feature_index", 3),
    ("Every occurrence of the warning flag",         "find_all",       "feature_index", 3),
    ("All occurrences of restart in the logs",       "find_all",       "feature_index", 3),
    ("Show every server that responded",             "find_all",       "feature_index", 3),

    # --- Priority 4: section keywords ---
    ("What does section 3 say about caching?",       "section_lookup", "section_index", 4),
    ("Summarise chapter 2",                          "section_lookup", "section_index", 4),
    ("In part one, what is covered?",               "section_lookup", "section_index", 4),
    ("Under heading Installation, what steps exist?","section_lookup", "section_index", 4),
    ("Find the section on authentication",           "section_lookup", "section_index", 4),

    # --- Priority 5: page keywords ---
    ("What is on page 12?",                         "page_lookup",    "page_index",    5),
    ("Show page 45",                                "page_lookup",    "page_index",    5),
    ("On page 3 there is a diagram",                "page_lookup",    "page_index",    5),
    ("What is the page number for the glossary?",   "page_lookup",    "page_index",    5),

    # --- Priority 6: default ---
    ("What is the retry policy?",                   "page_lookup",    "page_index",    6),
    ("How does authentication work?",               "page_lookup",    "page_index",    6),
    ("Explain the deployment process",              "page_lookup",    "page_index",    6),
    ("What does SSL stand for?",                    "page_lookup",    "page_index",    6),

    # --- Ambiguous / edge cases ---
    # IP beats table_keywords (priority 1 wins)
    ("Show the table for 10.1.2.3",                "table_query",    "table_index",   1),
    # "list all" beats "section" (priority 3 wins)
    ("List all sections in the document",           "find_all",       "feature_index", 3),
    # "page" beats default (priority 5 wins)
    ("What topic is discussed near page 7?",        "page_lookup",    "page_index",    5),
    # "chapter" beats "page" (priority 4 wins)
    ("Which page does chapter 4 start on?",         "section_lookup", "section_index", 4),
]
# fmt: on


@pytest.mark.parametrize("query,exp_type,exp_index,exp_priority", CASES)
def test_router_classify(query: str, exp_type: str, exp_index: str, exp_priority: int) -> None:
    result = router.classify(query)
    assert result.query_type == exp_type, (
        f"query={query!r}\n  got type={result.query_type!r} (rule={result.matched_rule!r})\n"
        f"  expected type={exp_type!r}"
    )
    assert result.target_index == exp_index, (
        f"query={query!r}\n  got index={result.target_index!r}\n  expected index={exp_index!r}"
    )
    assert result.matched_priority == exp_priority, (
        f"query={query!r}\n  got priority={result.matched_priority}\n  expected priority={exp_priority}"
    )
