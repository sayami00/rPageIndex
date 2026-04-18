import pytest
from src.cleanup.whitespace import clean_whitespace, MIN_TEXT_LENGTH


def test_strips_leading_trailing():
    assert clean_whitespace("  hello world  ") == "hello world"


def test_collapses_internal_spaces():
    assert clean_whitespace("hello   world") == "hello world"


def test_collapses_tabs():
    assert clean_whitespace("hello\t\tworld") == "hello world"


def test_collapses_excess_blank_lines():
    result = clean_whitespace("line1\n\n\n\nline2")
    assert result == "line1\n\nline2"


def test_nfc_normalization():
    # Compose "e" + combining acute into single char é — use long enough string
    composed = "\u00e9" * MIN_TEXT_LENGTH
    decomposed = ("e\u0301") * MIN_TEXT_LENGTH
    result = clean_whitespace(decomposed)
    assert result == composed


def test_returns_none_when_too_short():
    assert clean_whitespace("hi") is None
    assert clean_whitespace("    ") is None


def test_exactly_min_length_passes():
    text = "x" * MIN_TEXT_LENGTH
    assert clean_whitespace(text) == text


def test_empty_string_returns_none():
    assert clean_whitespace("") is None
