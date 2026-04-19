from __future__ import annotations

import logging
import math

from src.models.query import Candidate

logger = logging.getLogger(__name__)

_HEADER_TEMPLATE = (
    "Query: {query}\n\n"
    "Select the most relevant pages from the list below.\n"
    "Reply with ONLY the page numbers separated by commas. Example: 1, 3, 5\n\n"
)

_SNIPPET_LEN = 100
_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / _CHARS_PER_TOKEN))


def build_prompt(
    query: str,
    candidates: list[Candidate],
    page_texts: dict[str, str],
    max_tokens: int = 2000,
) -> tuple[str, int]:
    """
    Build numbered-list Ollama prompt within token budget.
    Returns (prompt_text, candidates_included_count).
    """
    header = _HEADER_TEMPLATE.format(query=query)
    budget_remaining = max_tokens - _estimate_tokens(header)

    lines: list[str] = []
    included = 0

    for i, candidate in enumerate(candidates, start=1):
        text = page_texts.get(candidate.page_id, "")
        snippet = text[:_SNIPPET_LEN].replace("\n", " ").strip()
        section = candidate.section_path or "(no section)"
        line = f"{i}. [Page {candidate.page_number}] {section} — {snippet}\n"

        cost = _estimate_tokens(line)
        if cost > budget_remaining:
            logger.info(
                "prompt_builder truncated at candidate %d/%d — token budget exhausted",
                i - 1, len(candidates),
            )
            break

        lines.append(line)
        budget_remaining -= cost
        included += 1

    prompt = header + "".join(lines)
    logger.debug("prompt_builder included=%d/%d tokens~=%d", included, len(candidates), _estimate_tokens(prompt))
    return prompt, included
