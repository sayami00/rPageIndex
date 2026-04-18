import pytest
from src.cleanup.deduplication import mark_duplicates, SIMILARITY_THRESHOLD


def _make_block(block_id: str, clean_text: str) -> dict:
    return {
        "block_id": block_id,
        "clean_text": clean_text,
        "is_duplicate": False,
        "duplicate_of": None,
    }


def test_no_duplicates_unchanged():
    blocks = [
        _make_block("b1", "The quick brown fox jumps over the lazy dog."),
        _make_block("b2", "A completely different sentence about something else."),
    ]
    result = mark_duplicates(blocks)
    assert not result[0]["is_duplicate"]
    assert not result[1]["is_duplicate"]


def test_exact_duplicate_flagged():
    text = "This sentence appears twice in the document as an exact duplicate."
    blocks = [
        _make_block("b1", text),
        _make_block("b2", text),
    ]
    result = mark_duplicates(blocks)
    assert not result[0]["is_duplicate"]
    assert result[1]["is_duplicate"]
    assert result[1]["duplicate_of"] == "b1"


def test_near_duplicate_flagged():
    blocks = [
        _make_block("b1", "The system processes requests in real-time using async handlers."),
        _make_block("b2", "The system processes requests in real-time using async handler."),
    ]
    result = mark_duplicates(blocks)
    assert result[1]["is_duplicate"]
    assert result[1]["duplicate_of"] == "b1"


def test_below_threshold_not_flagged():
    blocks = [
        _make_block("b1", "The quick brown fox jumps over the lazy dog."),
        _make_block("b2", "An entirely separate paragraph about a different topic altogether."),
    ]
    result = mark_duplicates(blocks)
    assert not result[1]["is_duplicate"]


def test_short_texts_skipped():
    # texts shorter than _MIN_TEXT_LEN should not be deduped
    blocks = [
        _make_block("b1", "hi"),
        _make_block("b2", "hi"),
    ]
    result = mark_duplicates(blocks)
    assert not result[1]["is_duplicate"]


def test_first_occurrence_kept():
    text = "Repeated content that appears multiple times throughout the document pages."
    blocks = [_make_block(f"b{i}", text) for i in range(3)]
    result = mark_duplicates(blocks)
    assert not result[0]["is_duplicate"]
    assert result[1]["is_duplicate"] and result[1]["duplicate_of"] == "b0"
    assert result[2]["is_duplicate"] and result[2]["duplicate_of"] == "b0"
