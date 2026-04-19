from __future__ import annotations

import logging
import re

from src.query.models import ClassifiedQuery

logger = logging.getLogger(__name__)

_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_RULES: list[tuple[int, str, re.Pattern | None, list[str], str, str]] = [
    # (priority, label, compiled_pattern, keywords, query_type, target_index)
    (
        1,
        "ip_address",
        _IP_RE,
        [],
        "table_query",
        "table_index",
    ),
    (
        2,
        "table_keywords",
        None,
        ["table", "row", "column", "cell"],
        "table_query",
        "table_index",
    ),
    (
        3,
        "find_all_keywords",
        None,
        ["list all", "find all", "every", "all occurrences"],
        "find_all",
        "feature_index",
    ),
    (
        4,
        "section_keywords",
        None,
        ["section", "chapter", "in part", "under heading"],
        "section_lookup",
        "section_index",
    ),
    (
        5,
        "page_keywords",
        None,
        ["page", "on page", "page number"],
        "page_lookup",
        "page_index",
    ),
]

_DEFAULT_RULE = (6, "default", "page_lookup", "page_index")


def _matches(query_lower: str, pattern: re.Pattern | None, keywords: list[str]) -> bool:
    if pattern is not None and pattern.search(query_lower):
        return True
    for kw in keywords:
        if kw in query_lower:
            return True
    return False


class QueryRouter:
    def classify(self, query: str) -> ClassifiedQuery:
        q = query.lower()

        for priority, label, pattern, keywords, query_type, target_index in _RULES:
            if _matches(q, pattern, keywords):
                result = ClassifiedQuery(
                    original=query,
                    query_type=query_type,
                    target_index=target_index,
                    matched_priority=priority,
                    matched_rule=label,
                )
                logger.info(
                    "classify query=%r rule=%r priority=%d type=%s index=%s",
                    query,
                    label,
                    priority,
                    query_type,
                    target_index,
                )
                return result

        priority, label, query_type, target_index = _DEFAULT_RULE
        result = ClassifiedQuery(
            original=query,
            query_type=query_type,
            target_index=target_index,
            matched_priority=priority,
            matched_rule=label,
        )
        logger.info(
            "classify query=%r rule=%r priority=%d type=%s index=%s",
            query,
            label,
            priority,
            query_type,
            target_index,
        )
        return result
