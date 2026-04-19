from __future__ import annotations

import pytest

from src.answer.citation_parser import parse_citations, split_answer_body


# ── parse_citations ────────────────────────────────────────────────────────────

def test_parse_single_citation() -> None:
    raw = "The cache size is 4GB.\n\nCITATIONS:\n- [file: doc.pdf, page: 12]"
    result = parse_citations(raw)
    assert result == ["[file: doc.pdf, page: 12]"]


def test_parse_multiple_citations() -> None:
    raw = (
        "The answer spans two pages.\n\n"
        "CITATIONS:\n"
        "- [file: doc.pdf, page: 3]\n"
        "- [file: doc.pdf, page: 7]"
    )
    result = parse_citations(raw)
    assert len(result) == 2
    assert "[file: doc.pdf, page: 3]" in result
    assert "[file: doc.pdf, page: 7]" in result


def test_parse_citations_case_insensitive_header() -> None:
    raw = "Answer.\n\ncitations:\n- [file: a.pdf, page: 1]"
    assert parse_citations(raw) == ["[file: a.pdf, page: 1]"]


def test_parse_no_citations_block() -> None:
    raw = "Just an answer with no citations."
    assert parse_citations(raw) == []


def test_parse_citations_block_but_no_valid_lines() -> None:
    raw = "Answer.\n\nCITATIONS:\n- nothing valid here"
    assert parse_citations(raw) == []


def test_parse_citation_with_spaces_around_file() -> None:
    raw = "A.\n\nCITATIONS:\n- [file:  report.pdf , page: 5]"
    result = parse_citations(raw)
    assert len(result) == 1
    assert "report.pdf" in result[0]
    assert "page: 5" in result[0]


def test_parse_ignores_text_before_citations() -> None:
    raw = "Some [file: fake.pdf, page: 99] in prose.\n\nCITATIONS:\n- [file: real.pdf, page: 1]"
    result = parse_citations(raw)
    # only citation in CITATIONS block returned
    assert result == ["[file: real.pdf, page: 1]"]


def test_parse_citations_multiple_files() -> None:
    raw = (
        "Answer.\n\nCITATIONS:\n"
        "- [file: alpha.pdf, page: 2]\n"
        "- [file: beta.pdf, page: 10]\n"
        "- [file: gamma.pdf, page: 4]"
    )
    result = parse_citations(raw)
    assert len(result) == 3


# ── split_answer_body ─────────────────────────────────────────────────────────

def test_split_body_before_citations() -> None:
    raw = "The answer is X.\n\nCITATIONS:\n- [file: doc.pdf, page: 1]"
    body = split_answer_body(raw)
    assert body == "The answer is X."
    assert "CITATIONS" not in body


def test_split_body_no_citations_block_returns_full() -> None:
    raw = "Just an answer."
    assert split_answer_body(raw) == "Just an answer."


def test_split_body_stripped() -> None:
    raw = "  The answer.  \n\nCITATIONS:\n- [file: doc.pdf, page: 1]"
    body = split_answer_body(raw)
    assert not body.startswith(" ")
    assert not body.endswith(" ")


def test_split_body_multiline_answer() -> None:
    raw = "Line one.\nLine two.\nLine three.\n\nCITATIONS:\n- [file: doc.pdf, page: 3]"
    body = split_answer_body(raw)
    assert "Line one." in body
    assert "Line two." in body
    assert "Line three." in body
    assert "CITATIONS" not in body
