from __future__ import annotations

import logging
import math
from collections import defaultdict

from src.models.exceptions import EmptyEvidenceError
from src.models.index import PageRecord
from src.models.query import Candidate, Evidence

logger = logging.getLogger(__name__)

MAX_EVIDENCE_TOKENS = 3000
_CHARS_PER_TOKEN = 4


def _score(c: Candidate) -> float:
    return c.final_score if c.final_score is not None else c.bm25_normalized


def _count_tokens(page: PageRecord) -> int:
    text = f"{page.body_text} {page.table_text}".strip()
    return max(1, math.ceil(len(text) / _CHARS_PER_TOKEN))


def _truncate_page(page: PageRecord, remaining_tokens: int) -> PageRecord:
    max_chars = remaining_tokens * _CHARS_PER_TOKEN
    combined = f"{page.body_text} {page.table_text}".strip()
    cut = combined[:max_chars]
    new_search = f"{page.heading_text} {cut}".strip()
    return page.model_copy(update={
        "body_text": cut,
        "table_text": "",
        "page_search_text": new_search,
        "truncated": True,
    })


def _group_by_section(pages: list[PageRecord]) -> list[PageRecord]:
    groups: dict[str, list[PageRecord]] = {}
    order: list[str] = []
    for p in pages:
        key = p.section_path or ""
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(p)
    result: list[PageRecord] = []
    for key in order:
        result.extend(sorted(groups[key], key=lambda p: p.page_number))
    return result


class EvidenceAssembler:
    def __init__(self, token_budget: int = MAX_EVIDENCE_TOKENS) -> None:
        self._token_budget = token_budget

    def assemble(
        self,
        candidates: list[Candidate],
        page_records: dict[str, PageRecord],
        query_type: str,
    ) -> Evidence:
        logger.info(
            "assemble candidates_in=%d query_type=%s",
            len(candidates), query_type,
        )

        # Step 1: deduplicate by page_id — keep highest-scored
        unique: dict[str, Candidate] = {}
        for c in candidates:
            if c.page_id not in unique or _score(c) > _score(unique[c.page_id]):
                unique[c.page_id] = c
        deduped = sorted(unique.values(), key=_score, reverse=True)
        logger.info("assemble unique=%d after_dedup", len(deduped))

        # Step 2 + 3: token budget pass (score-descending)
        included: list[PageRecord] = []
        total_tokens = 0
        budget_hit = False
        dropped = 0

        for c in deduped:
            rec = page_records.get(c.page_id)
            if rec is None:
                logger.warning("assemble page_id=%r not found in page_records — dropped", c.page_id)
                dropped += 1
                continue

            remaining = self._token_budget - total_tokens
            if remaining <= 0:
                logger.info("assemble page_id=%r DROPPED remaining=0", c.page_id)
                dropped += 1
                continue

            page_tokens = _count_tokens(rec)
            if page_tokens <= remaining:
                included.append(rec)
                total_tokens += page_tokens
                logger.info(
                    "assemble page_id=%r tokens=%d cumulative=%d/%d",
                    c.page_id, page_tokens, total_tokens, self._token_budget,
                )
            else:
                truncated = _truncate_page(rec, remaining)
                included.append(truncated)
                total_tokens += remaining
                budget_hit = True
                logger.info(
                    "assemble page_id=%r TRUNCATED tokens=%d->%d budget_hit=True cumulative=%d/%d",
                    c.page_id, page_tokens, remaining, total_tokens, self._token_budget,
                )

        # Step 4: reorder — group by section, sort by page_number within group
        ordered = _group_by_section(included)

        logger.info(
            "assemble assembled pages=%d total_tokens=%d/%d budget_hit=%s dropped=%d",
            len(ordered), total_tokens, self._token_budget, budget_hit, dropped,
        )

        if not ordered:
            raise EmptyEvidenceError(
                "Evidence.pages is empty — Ollama must not be called. "
                "Return not_found response instead."
            )

        return Evidence(
            pages=ordered,
            total_tokens=total_tokens,
            token_budget=self._token_budget,
            token_budget_hit=budget_hit,
            pages_dropped=dropped,
            query_type=query_type,
        )
