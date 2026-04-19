from __future__ import annotations

import logging

from src.models.query import Candidate
from src.reasoning.ollama_client import OllamaClient, OllamaError
from src.reasoning.page_expander import expand_pages
from src.reasoning.prompt_builder import build_prompt
from src.reasoning.response_parser import parse_selected_numbers
from src.reasoning.tree_subset import build_tree_subset
from src.section_tree.models import SectionTree

logger = logging.getLogger(__name__)

_FALLBACK_TOP_N = 3


class ReasoningLayer:
    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    def select(
        self,
        query: str,
        candidates: list[Candidate],
        page_texts: dict[str, str],
        tree: SectionTree | None = None,
    ) -> list[Candidate]:
        """
        Run one Ollama call to select the most relevant candidates,
        then expand selection to adjacent same-section pages.

        Falls back to top-3 reranker results on network error or
        unparseable Ollama response.
        """
        if not candidates:
            return []

        # Step 1: compact tree context (informational — kept for future prompt enrichment)
        if tree is not None:
            _subset = build_tree_subset(candidates, tree)
            logger.debug("tree_subset nodes=%d", len(_subset))

        # Step 2: build prompt
        prompt, included_count = build_prompt(query, candidates, page_texts)
        prompt_tokens = len(prompt) // 4

        logger.info(
            "reasoning query=%r candidates_in=%d included_in_prompt=%d prompt_tokens=%d model=%s",
            query, len(candidates), included_count, prompt_tokens, self._client.model,
        )

        # Step 3: call Ollama
        try:
            raw_response = self._client.generate(prompt)
        except OllamaError as exc:
            logger.warning(
                "ollama_fallback=network_error error=%s using top-%d reranker results",
                exc, _FALLBACK_TOP_N,
            )
            return candidates[:_FALLBACK_TOP_N]

        # Step 4: parse numbers
        selected_numbers = parse_selected_numbers(raw_response, max_n=included_count)
        if not selected_numbers:
            logger.warning(
                "ollama_fallback=parse_failure response=%r using top-%d reranker results",
                raw_response[:200], _FALLBACK_TOP_N,
            )
            return candidates[:_FALLBACK_TOP_N]

        logger.info("ollama_response=%r selected_numbers=%s", raw_response[:200], selected_numbers)

        # Step 5: map 1-based numbers → candidates
        selected = [candidates[n - 1] for n in selected_numbers if n - 1 < len(candidates)]

        # Step 6: expand to adjacent same-section pages
        expanded = expand_pages(selected, candidates, tree)

        logger.info(
            "reasoning selected=%d expanded=%d",
            len(selected), len(expanded),
        )
        return expanded
