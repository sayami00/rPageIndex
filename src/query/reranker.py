from __future__ import annotations

import logging

from src.models.query import Candidate

logger = logging.getLogger(__name__)

_TOP_N: dict[str, int] = {
    "page_lookup":    5,
    "section_lookup": 5,
    "table_query":    5,
    "find_all":       8,
}

_W_BM25      = 0.5
_W_HIERARCHY = 0.3
_W_PROXIMITY = 0.2


class StructuralReranker:
    """
    Rescore a BM25 candidate list using structure signals.

    Scoring:
        bm25_normalized  = raw / max_raw   (0-1)
        hierarchy_score  = section path overlap with query hint, or 0.5 neutral
        proximity_score  = fraction of ±2-page neighbours also in candidate set
        final_score      = 0.5*bm25 + 0.3*hierarchy + 0.2*proximity
    """

    def rerank(
        self,
        candidates: list[Candidate],
        query_type: str,
        section_hint: str | None = None,
    ) -> list[Candidate]:
        if not candidates:
            return []

        # --- normalize BM25 ---
        max_raw = max(c.bm25_raw for c in candidates) or 1.0
        normed: list[Candidate] = [
            c.model_copy(update={"bm25_normalized": c.bm25_raw / max_raw})
            for c in candidates
        ]

        # --- build page-number set for proximity ---
        page_numbers: set[int] = {c.page_number for c in normed}

        # --- score each candidate ---
        scored: list[Candidate] = []
        for c in normed:
            h = _hierarchy_score(c.section_path, section_hint)
            p = _proximity_score(c.page_number, page_numbers)
            final = _W_BM25 * c.bm25_normalized + _W_HIERARCHY * h + _W_PROXIMITY * p
            scored.append(c.model_copy(update={
                "hierarchy_score": round(h, 4),
                "proximity_score": round(p, 4),
                "final_score":     round(final, 4),
            }))
            logger.debug(
                "rerank page_id=%r bm25=%.3f hierarchy=%.3f proximity=%.3f final=%.3f",
                c.page_id, c.bm25_normalized, h, p, final,
            )

        scored.sort(key=lambda c: c.final_score, reverse=True)  # type: ignore[arg-type]

        top_n = _TOP_N.get(query_type, 5)
        result = scored[:top_n]

        logger.info(
            "rerank query_type=%s section_hint=%r candidates_in=%d top_n=%d",
            query_type, section_hint, len(candidates), top_n,
        )
        _log_top3(result)
        return result


# ── helpers ────────────────────────────────────────────────────────────────────

def _hierarchy_score(section_path: str, hint: str | None) -> float:
    if not hint:
        return 0.5  # neutral — no section hint detected
    if not section_path:
        return 0.0

    hint_words  = set(hint.lower().split())
    path_words  = set(section_path.lower().replace("/", " ").replace(">", " ").split())
    overlap     = hint_words & path_words
    if not hint_words:
        return 0.5
    return min(len(overlap) / len(hint_words), 1.0)


def _proximity_score(page_number: int, all_pages: set[int]) -> float:
    neighbours = sum(
        1 for offset in (-2, -1, 1, 2)
        if (page_number + offset) in all_pages
    )
    return min(neighbours / 2, 1.0)


def _log_top3(candidates: list[Candidate]) -> None:
    for rank, c in enumerate(candidates[:3], start=1):
        logger.info(
            "top%d page_id=%r bm25=%.3f hierarchy=%.3f proximity=%.3f final=%.3f",
            rank, c.page_id,
            c.bm25_normalized,
            c.hierarchy_score,
            c.proximity_score,
            c.final_score,
        )
