import pytest
from src.cleanup.classifier import classify_block


def test_table_hint_wins():
    assert classify_block("col1 col2", type_hint="table") == "table"


def test_heading_1_hint_wins():
    assert classify_block("Introduction", type_hint="heading_1") == "heading_1"


def test_heading_2_hint_wins():
    assert classify_block("Background", type_hint="heading_2") == "heading_2"


def test_page_number():
    assert classify_block("42") == "page_number"
    assert classify_block("Page 3 of 10") == "page_number"
    assert classify_block("page 1") == "page_number"


def test_caption():
    assert classify_block("Figure 1 System Architecture") == "caption"
    assert classify_block("Table 3 Results Summary") == "caption"
    assert classify_block("Fig. 2 Overview") == "caption"


def test_bullet_list_item():
    assert classify_block("• First item in list") == "list_item"
    assert classify_block("- Another item") == "list_item"
    assert classify_block("* Yet another") == "list_item"


def test_numbered_list_item():
    assert classify_block("1. First step") == "list_item"
    assert classify_block("2) Second step") == "list_item"


def test_table_by_tabs():
    assert classify_block("col1\tcol2\tcol3") == "table"


def test_all_caps_heading_heuristic():
    assert classify_block("INTRODUCTION") == "heading_1"
    assert classify_block("SYSTEM OVERVIEW") == "heading_1"


def test_normal_paragraph():
    assert classify_block(
        "This is a normal paragraph with multiple sentences. It should be classified as paragraph."
    ) == "paragraph"


def test_long_all_caps_is_paragraph():
    long = "THIS IS A VERY LONG ALL CAPS TEXT THAT EXCEEDS THE HEADING LENGTH LIMIT AND SHOULD NOT BE CLASSIFIED AS A HEADING AT ALL"
    # Over 120 chars or 15 words → paragraph
    assert classify_block(long) == "paragraph"
