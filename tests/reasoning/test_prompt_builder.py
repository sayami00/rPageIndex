from __future__ import annotations

import pytest

from src.models.query import Candidate
from src.reasoning.prompt_builder import _CHARS_PER_TOKEN, build_prompt


def _cand(page: int, section: str = "chapter 1") -> Candidate:
    return Candidate(
        page_id=f"doc::p{page}", doc_id="doc", source_file="doc.pdf",
        page_number=page, section_path=section,
        bm25_raw=1.0, bm25_normalized=1.0,
    )


def _texts(candidates: list[Candidate], text: str = "Sample body text for this page.") -> dict[str, str]:
    return {c.page_id: text for c in candidates}


def test_prompt_contains_query() -> None:
    cands = [_cand(1)]
    prompt, _ = build_prompt("What is caching?", cands, _texts(cands))
    assert "What is caching?" in prompt


def test_prompt_contains_numbered_entries() -> None:
    cands = [_cand(1), _cand(2), _cand(3)]
    prompt, _ = build_prompt("query", cands, _texts(cands))
    assert "1." in prompt
    assert "2." in prompt
    assert "3." in prompt


def test_prompt_shows_page_number_and_section() -> None:
    cands = [_cand(12, "chapter 3 / caching")]
    prompt, _ = build_prompt("query", cands, _texts(cands))
    assert "Page 12" in prompt
    assert "chapter 3 / caching" in prompt


def test_snippet_truncated_to_100_chars() -> None:
    long_text = "A" * 200
    cands = [_cand(1)]
    prompt, _ = build_prompt("query", cands, {cands[0].page_id: long_text})
    assert "A" * 101 not in prompt  # no more than 100 A's in prompt entry


def test_missing_text_uses_empty_snippet() -> None:
    cands = [_cand(1)]
    prompt, _ = build_prompt("query", cands, {})
    assert "1." in prompt  # entry still appears, just empty snippet


def test_no_section_path_shows_no_section_label() -> None:
    cand = Candidate(
        page_id="doc::p5", doc_id="doc", source_file="doc.pdf",
        page_number=5, section_path="",
        bm25_raw=1.0, bm25_normalized=1.0,
    )
    prompt, _ = build_prompt("query", [cand], {cand.page_id: "text"})
    assert "(no section)" in prompt


def test_token_budget_respected() -> None:
    # 50 candidates with long text — should be truncated to fit budget
    cands = [_cand(i) for i in range(1, 51)]
    long_text = "X" * 400
    texts = {c.page_id: long_text for c in cands}
    prompt, included = build_prompt("query", cands, texts, max_tokens=500)
    estimated_tokens = len(prompt) // _CHARS_PER_TOKEN
    assert estimated_tokens <= 500
    assert included < 50


def test_included_count_matches_entries_in_prompt() -> None:
    cands = [_cand(i) for i in range(1, 6)]
    prompt, included = build_prompt("query", cands, _texts(cands))
    # All 5 should fit comfortably in 2000 tokens
    assert included == 5
    for i in range(1, 6):
        assert f"{i}." in prompt
