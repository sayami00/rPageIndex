from __future__ import annotations

import logging
import math
import time

from src.answer.citation_parser import parse_citations, split_answer_body
from src.answer.prompt_builder import build_answer_prompt
from src.models.answer import RawAnswer
from src.models.query import Evidence
from src.reasoning.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN = 4


class AnswerGenerator:
    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    def generate(
        self,
        query: str,
        query_type: str,
        evidence: Evidence,
    ) -> RawAnswer:
        """
        Build prompt → call Ollama → parse citations → return RawAnswer.
        Raises OllamaError on network/timeout failure — caller handles.
        """
        prompt = build_answer_prompt(query, query_type, evidence)
        input_tokens = math.ceil(len(prompt) / _CHARS_PER_TOKEN)

        logger.info(
            "generate query_type=%s evidence_pages=%d input_tokens=%d model=%s",
            query_type, len(evidence.pages), input_tokens, self._client.model,
        )

        t0 = time.monotonic()
        raw_response = self._client.generate(prompt)
        latency_ms = int((time.monotonic() - t0) * 1000)

        output_tokens = math.ceil(len(raw_response) / _CHARS_PER_TOKEN)
        answer_body = split_answer_body(raw_response)
        raw_citations = parse_citations(raw_response)

        logger.info(
            "generate latency_ms=%d output_tokens=%d citations=%d",
            latency_ms, output_tokens, len(raw_citations),
        )
        logger.info("citation_parse raw_citations=%s", raw_citations)

        return RawAnswer(
            answer_text=raw_response,
            answer_body=answer_body,
            raw_citations=raw_citations,
            model_used=self._client.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            token_budget_hit=evidence.token_budget_hit,
        )
