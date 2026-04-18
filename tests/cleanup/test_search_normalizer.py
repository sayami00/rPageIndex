import pytest
from src.cleanup.search_normalizer import build_search_text


def test_lowercases_text():
    result = build_search_text("Hello World")
    assert result == result.lower()


def test_strips_punctuation():
    result = build_search_text("Hello, world! How are you?")
    assert "," not in result
    assert "!" not in result
    assert "?" not in result


def test_collapses_spaces():
    result = build_search_text("too   many   spaces")
    assert "  " not in result


def test_expands_abbreviation():
    result = build_search_text("See fig 3 for details")
    assert "figure" in result


def test_expands_ref_abbreviation():
    result = build_search_text("As per req 4.2")
    assert "requirement" in result


def test_empty_string():
    assert build_search_text("") == ""


def test_no_leading_trailing_space():
    result = build_search_text("  some text  ")
    assert result == result.strip()
