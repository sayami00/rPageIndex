import pytest
from src.cleanup.list_cleanup import normalize_list_item


@pytest.mark.parametrize("bullet", ["•", "◦", "▪", "►", "·", "–", "—", "*"])
def test_bullet_chars_normalized_to_dash(bullet):
    text, kind = normalize_list_item(f"{bullet} Some item text")
    assert text.startswith("- ")
    assert kind == "unordered"


def test_numbered_item_preserved():
    text, kind = normalize_list_item("1. First item")
    assert text == "1. First item"
    assert kind == "ordered"


def test_numbered_paren_item():
    text, kind = normalize_list_item("3) Third item")
    assert text == "3) Third item"
    assert kind == "ordered"


def test_plain_text_unchanged():
    text, kind = normalize_list_item("No bullet here")
    assert text == "No bullet here"
    assert kind == "unordered"


def test_content_preserved_after_bullet():
    text, kind = normalize_list_item("• Important point about the system")
    assert text == "- Important point about the system"
