from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.answer.generator import AnswerGenerator
from src.models.answer import RawAnswer
from src.models.index import PageRecord
from src.models.query import Evidence
from src.reasoning.ollama_client import OllamaClient, OllamaError


def _make_page(page_number: int, body: str = "body text") -> PageRecord:
    search = f"Heading {body}".strip()
    return PageRecord(
        page_id=f"doc::p{page_number}",
        doc_id="doc",
        source_file="doc.pdf",
        page_number=page_number,
        heading_text="Heading",
        body_text=body,
        table_text="",
        page_search_text=search,
        section_path="chapter 1",
        quality_floor=1.0,
        has_low_confidence=False,
        table_ids=[],
        feature_ids=[],
        block_count=1,
    )


def _make_evidence(pages: list[PageRecord]) -> Evidence:
    total = sum(len(p.body_text) // 4 + 1 for p in pages)
    return Evidence(
        pages=pages,
        total_tokens=total,
        token_budget=3000,
        token_budget_hit=False,
        pages_dropped=0,
        query_type="page_lookup",
    )


def _mock_client(response: str = "The answer.\n\nCITATIONS:\n- [file: doc.pdf, page: 3]") -> OllamaClient:
    client = MagicMock(spec=OllamaClient)
    client.model = "qwen:7b"
    client.generate.return_value = response
    return client


_EV = _make_evidence([_make_page(3, "Some content about caching.")])


def test_generate_returns_raw_answer() -> None:
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("What is caching?", "page_lookup", _EV)
    assert isinstance(result, RawAnswer)


def test_generate_answer_text_is_full_response() -> None:
    raw = "The answer.\n\nCITATIONS:\n- [file: doc.pdf, page: 3]"
    gen = AnswerGenerator(_mock_client(raw))
    result = gen.generate("query", "page_lookup", _EV)
    assert result.answer_text == raw


def test_generate_answer_body_excludes_citations() -> None:
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("query", "page_lookup", _EV)
    assert "CITATIONS" not in result.answer_body
    assert "The answer." in result.answer_body


def test_generate_raw_citations_parsed() -> None:
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("query", "page_lookup", _EV)
    assert len(result.raw_citations) == 1
    assert "doc.pdf" in result.raw_citations[0]
    assert "page: 3" in result.raw_citations[0]


def test_generate_model_used_matches_client() -> None:
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("query", "page_lookup", _EV)
    assert result.model_used == "qwen:7b"


def test_generate_latency_ms_non_negative() -> None:
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("query", "page_lookup", _EV)
    assert result.latency_ms >= 0


def test_generate_input_tokens_positive() -> None:
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("query", "page_lookup", _EV)
    assert result.input_tokens > 0


def test_generate_output_tokens_positive() -> None:
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("query", "page_lookup", _EV)
    assert result.output_tokens > 0


def test_generate_token_budget_hit_propagated() -> None:
    pages = [_make_page(i) for i in range(1, 4)]
    total = sum(len(p.body_text) // 4 + 1 for p in pages)
    ev_hit = Evidence(
        pages=pages,
        total_tokens=total,
        token_budget=3000,
        token_budget_hit=True,
        pages_dropped=2,
        query_type="page_lookup",
    )
    gen = AnswerGenerator(_mock_client())
    result = gen.generate("query", "page_lookup", ev_hit)
    assert result.token_budget_hit is True


def test_generate_no_citations_block_empty_list() -> None:
    gen = AnswerGenerator(_mock_client("Just an answer with no citations block."))
    result = gen.generate("query", "page_lookup", _EV)
    assert result.raw_citations == []
    assert result.answer_body == "Just an answer with no citations block."


def test_generate_ollama_error_propagates() -> None:
    client = MagicMock(spec=OllamaClient)
    client.model = "qwen:7b"
    client.generate.side_effect = OllamaError("connection refused")
    gen = AnswerGenerator(client)
    with pytest.raises(OllamaError):
        gen.generate("query", "page_lookup", _EV)


def test_generate_calls_ollama_exactly_once() -> None:
    client = _mock_client()
    gen = AnswerGenerator(client)
    gen.generate("query", "page_lookup", _EV)
    client.generate.assert_called_once()
