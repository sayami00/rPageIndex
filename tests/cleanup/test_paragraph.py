import pytest
from src.cleanup.paragraph import reconstruct_paragraphs


def test_joins_broken_line():
    text = "The quick brown fox\njumps over the lazy dog"
    result = reconstruct_paragraphs(text)
    assert result == "The quick brown fox jumps over the lazy dog"


def test_does_not_join_after_sentence_end():
    text = "The fox ran fast.\nThe dog barked."
    result = reconstruct_paragraphs(text)
    assert result == text


def test_does_not_join_when_next_starts_uppercase():
    text = "End of section.\nNew Section Starts Here"
    result = reconstruct_paragraphs(text)
    assert result == text


def test_single_line_unchanged():
    text = "Nothing to reconstruct here."
    assert reconstruct_paragraphs(text) == text


def test_multiple_broken_lines_joined():
    text = "This is a long sentence that was\nbroken across multiple lines by\nthe PDF extractor"
    result = reconstruct_paragraphs(text)
    assert result == "This is a long sentence that was broken across multiple lines by the PDF extractor"


def test_paragraph_boundary_preserved():
    text = "First paragraph ends here.\n\nSecond paragraph starts here."
    result = reconstruct_paragraphs(text)
    assert "First paragraph ends here." in result
    assert "Second paragraph starts here." in result
