from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.models.query import Candidate
from src.reasoning.ollama_client import OllamaClient, OllamaError
from src.reasoning.pipeline import ReasoningLayer


def _cand(page: int, section: str = "chapter 1") -> Candidate:
    return Candidate(
        page_id=f"doc::p{page}", doc_id="doc", source_file="doc.pdf",
        page_number=page, section_path=section,
        bm25_raw=float(10 - page), bm25_normalized=0.9,
    )


def _mock_client(response: str = "1, 3") -> OllamaClient:
    client = MagicMock(spec=OllamaClient)
    client.model = "qwen:7b"
    client.generate.return_value = response
    return client


_CANDIDATES = [_cand(5), _cand(6), _cand(7), _cand(8), _cand(9)]
_PAGE_TEXTS = {c.page_id: f"Text for page {c.page_number}." for c in _CANDIDATES}


def test_ollama_selected_candidates_returned() -> None:
    client = _mock_client("1, 3")  # pages 5 and 7 selected (1-based)
    layer = ReasoningLayer(client)
    result = layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    pages = {c.page_number for c in result}
    assert 5 in pages  # candidate 1
    assert 7 in pages  # candidate 3


def test_adjacent_pages_expanded() -> None:
    # Select page 6 (candidate 2) — page 5 and 7 are adjacent, same section → added
    client = _mock_client("2")
    layer = ReasoningLayer(client)
    result = layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    pages = {c.page_number for c in result}
    assert 5 in pages or 7 in pages  # at least one adjacent added


def test_fallback_on_ollama_error() -> None:
    client = MagicMock(spec=OllamaClient)
    client.model = "qwen:7b"
    client.generate.side_effect = OllamaError("connection refused")
    layer = ReasoningLayer(client)
    result = layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    # Should return top-3 candidates
    assert len(result) == 3
    assert result[0].page_number == _CANDIDATES[0].page_number


def test_fallback_on_unparseable_response() -> None:
    client = _mock_client("The model has no opinion.")
    layer = ReasoningLayer(client)
    result = layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    assert len(result) == 3
    assert result[0].page_number == _CANDIDATES[0].page_number


def test_empty_candidates_returns_empty() -> None:
    layer = ReasoningLayer(_mock_client())
    result = layer.select("query", [], {})
    assert result == []


def test_out_of_range_numbers_ignored() -> None:
    client = _mock_client("1, 99, 100")  # 99 and 100 > len(candidates)=5
    layer = ReasoningLayer(client)
    result = layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    # Only candidate 1 (page 5) selected — no crash
    pages = {c.page_number for c in result}
    assert 5 in pages


def test_result_sorted_by_page_number() -> None:
    client = _mock_client("3, 1")  # reverse order
    layer = ReasoningLayer(client)
    result = layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    pages = [c.page_number for c in result]
    assert pages == sorted(pages)


def test_ollama_generate_called_once() -> None:
    client = _mock_client("1")
    layer = ReasoningLayer(client)
    layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    client.generate.assert_called_once()


def test_logging_includes_key_fields(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    client = _mock_client("1, 2")
    layer = ReasoningLayer(client)
    with caplog.at_level(logging.INFO, logger="src.reasoning.pipeline"):
        layer.select("test query", _CANDIDATES, _PAGE_TEXTS)
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "test query" in messages
    assert "candidates_in" in messages
    assert "selected" in messages


def test_logging_records_fallback_reason(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    client = _mock_client("no numbers here")
    layer = ReasoningLayer(client)
    with caplog.at_level(logging.WARNING, logger="src.reasoning.pipeline"):
        layer.select("query", _CANDIDATES, _PAGE_TEXTS)
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "parse_failure" in messages
