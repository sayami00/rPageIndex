from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.section_tree.builder import build_tree
from src.section_tree.cache import SummaryCache
from src.section_tree.summarizer import (
    _body_snippet,
    _truncate_to_budget,
    flatten_nodes,
    generate_summaries,
)
from tests.section_tree.conftest import make_block


# ── helpers ──────────────────────────────────────────────────────────────────

def _tree_with_headings(total_pages=10):
    headings = [
        make_block("h1", "heading_1", "Introduction", page_number=1, sequence=0),
        make_block("h2", "heading_2", "Background", page_number=2, sequence=1),
    ]
    body = [
        make_block("p1", "paragraph", "Some body text here.", page_number=1, sequence=2),
        make_block("p2", "paragraph", "Background details here.", page_number=2, sequence=3),
    ]
    all_blocks = headings + body
    from src.section_tree.detector import extract_headings
    h = extract_headings(all_blocks)
    tree = build_tree(h, "doc1", "f.pdf", total_pages)
    return tree, all_blocks


def _make_cache(tmp_path):
    return SummaryCache(cache_dir=str(tmp_path), doc_id="doc1")


# ── body_snippet ─────────────────────────────────────────────────────────────

def test_body_snippet_returns_first_paragraph_in_span():
    node = flatten_nodes(
        build_tree(
            [make_block("h1", "heading_1", "Intro", page_number=1, sequence=0)],
            "doc1", "f.pdf", 5,
        ).root
    )[0]
    blocks = [
        make_block("p1", "paragraph", "First body paragraph.", page_number=1, sequence=1),
        make_block("p2", "paragraph", "Second paragraph.", page_number=2, sequence=2),
    ]
    snippet = _body_snippet(node, blocks)
    assert snippet == "First body paragraph."


def test_body_snippet_empty_when_no_paragraph_in_span():
    node = flatten_nodes(
        build_tree(
            [make_block("h1", "heading_1", "Empty", page_number=5, sequence=0)],
            "doc1", "f.pdf", 5,
        ).root
    )[0]
    blocks = [make_block("p1", "paragraph", "Text", page_number=1, sequence=0)]
    assert _body_snippet(node, blocks) == ""


def test_body_snippet_excludes_reject():
    node = flatten_nodes(
        build_tree(
            [make_block("h1", "heading_1", "Section", page_number=1, sequence=0)],
            "doc1", "f.pdf", 5,
        ).root
    )[0]
    blocks = [
        make_block("p1", "paragraph", "Rejected.", page_number=1, sequence=1, gate_status="REJECT"),
        make_block("p2", "paragraph", "Good content.", page_number=1, sequence=2, gate_status="PASS"),
    ]
    assert _body_snippet(node, blocks) == "Good content."


# ── truncate_to_budget ────────────────────────────────────────────────────────

def test_truncate_short_content_unchanged():
    result = _truncate_to_budget("Title", "Short body.")
    assert result == "Short body."


def test_truncate_long_body_shortened():
    title = "T" * 10
    body = "B" * 10000
    result = _truncate_to_budget(title, body)
    assert len(result) < len(body)


def test_truncate_returns_empty_when_title_consumes_all_budget():
    title = "T" * 2000  # way over budget
    result = _truncate_to_budget(title, "some body")
    assert result == ""


# ── generate_summaries (mocked Ollama) ───────────────────────────────────────

def _mock_response(text: str):
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_resp.json = AsyncMock(return_value={"response": text})
    return mock_resp


def _mock_session(response_text: str = "A one-sentence summary."):
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.post = MagicMock(return_value=_mock_response(response_text))
    return session


@pytest.mark.asyncio
async def test_summaries_populated(tmp_path):
    tree, blocks = _tree_with_headings()
    cache = _make_cache(tmp_path)

    with patch("src.section_tree.summarizer.aiohttp.ClientSession", return_value=_mock_session("Summary text.")):
        await generate_summaries(tree, blocks, cache, "http://localhost", "llama3.2", 5)

    nodes = flatten_nodes(tree.root)
    assert all(n.summary != "" for n in nodes)


@pytest.mark.asyncio
async def test_cache_hit_skips_ollama(tmp_path):
    tree, blocks = _tree_with_headings()
    cache = _make_cache(tmp_path)

    mock_session = _mock_session("Cached summary.")
    with patch("src.section_tree.summarizer.aiohttp.ClientSession", return_value=mock_session):
        await generate_summaries(tree, blocks, cache, "http://localhost", "llama3.2", 5)

    # Reset summaries and run again — cache should prevent calls
    nodes = flatten_nodes(tree.root)
    for n in nodes:
        n.summary = ""

    fresh_cache = _make_cache(tmp_path)  # reload from disk
    call_count_before = mock_session.post.call_count

    with patch("src.section_tree.summarizer.aiohttp.ClientSession", return_value=mock_session):
        await generate_summaries(tree, blocks, fresh_cache, "http://localhost", "llama3.2", 5)

    # No new Ollama calls — all served from cache
    assert mock_session.post.call_count == call_count_before


@pytest.mark.asyncio
async def test_ollama_error_leaves_summary_empty(tmp_path):
    tree, blocks = _tree_with_headings()
    cache = _make_cache(tmp_path)

    error_session = AsyncMock()
    error_session.__aenter__ = AsyncMock(return_value=error_session)
    error_session.__aexit__ = AsyncMock(return_value=False)
    error_session.post = MagicMock(side_effect=Exception("connection refused"))

    with patch("src.section_tree.summarizer.aiohttp.ClientSession", return_value=error_session):
        # Must not raise
        await generate_summaries(tree, blocks, cache, "http://localhost", "llama3.2", 5)

    nodes = flatten_nodes(tree.root)
    assert all(n.summary == "" for n in nodes)


@pytest.mark.asyncio
async def test_no_nodes_no_ollama_call(tmp_path):
    tree = build_tree([], "doc1", "f.pdf", 5)
    cache = _make_cache(tmp_path)
    mock_session = _mock_session()

    with patch("src.section_tree.summarizer.aiohttp.ClientSession", return_value=mock_session):
        await generate_summaries(tree, [], cache, "http://localhost", "llama3.2", 5)

    mock_session.post.assert_not_called()
