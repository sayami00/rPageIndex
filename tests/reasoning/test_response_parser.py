from __future__ import annotations

import pytest

from src.reasoning.response_parser import parse_selected_numbers


@pytest.mark.parametrize("response,max_n,expected", [
    # clean comma-separated
    ("1, 3, 5", 5, [1, 3, 5]),
    # with explanatory text
    ("The most relevant pages are 2 and 4.", 5, [2, 4]),
    # out-of-range filtered
    ("1 6 10", 5, [1]),
    # zero excluded
    ("0 1 2", 5, [1, 2]),
    # duplicates deduped
    ("1, 1, 3, 3", 5, [1, 3]),
    # empty response
    ("", 5, []),
    # no numbers
    ("nothing here", 5, []),
    # single number
    ("3", 5, [3]),
    # all out of range
    ("8 9 10", 5, []),
    # numbers embedded in text
    ("I choose options 2, 4 from the given list.", 5, [2, 4]),
    # max_n = 1
    ("1 2 3", 1, [1]),
    # newline separated
    ("1\n2\n3", 3, [1, 2, 3]),
    # result sorted ascending
    ("5, 3, 1", 5, [1, 3, 5]),
])
def test_parse_selected_numbers(response: str, max_n: int, expected: list[int]) -> None:
    assert parse_selected_numbers(response, max_n) == expected
