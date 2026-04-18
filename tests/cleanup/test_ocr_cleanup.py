import pytest
from src.cleanup.ocr_cleanup import fix_ocr_text, is_low_confidence, OCR_CONFIDENCE_LOW_THRESHOLD


def test_zero_to_O_before_letter():
    assert fix_ocr_text("0pen the door") == "Open the door"


def test_one_to_I_before_letter():
    assert fix_ocr_text("1nstead of") == "Instead of"


def test_digit_in_pure_number_unchanged():
    # "100" should not be mangled
    result = fix_ocr_text("100 items")
    assert "100" in result


def test_multiple_substitutions():
    result = fix_ocr_text("0bject 1dentifier")
    assert "Object" in result
    assert "Identifier" in result


def test_no_change_on_clean_text():
    text = "The quick brown fox jumps over the lazy dog."
    assert fix_ocr_text(text) == text


def test_is_low_confidence_below_threshold():
    assert is_low_confidence(0.5) is True
    assert is_low_confidence(0.0) is True


def test_is_low_confidence_at_threshold():
    assert is_low_confidence(OCR_CONFIDENCE_LOW_THRESHOLD) is False


def test_is_low_confidence_above_threshold():
    assert is_low_confidence(0.9) is False


def test_is_low_confidence_none():
    assert is_low_confidence(None) is False
