from __future__ import annotations

import pytest

from src.models.query import Candidate
from src.reasoning.page_expander import expand_pages
from src.section_tree.models import SectionTree, TreeNode


def _cand(page: int, section: str = "chapter 1") -> Candidate:
    return Candidate(
        page_id=f"doc::p{page}", doc_id="doc", source_file="doc.pdf",
        page_number=page, section_path=section,
        bm25_raw=float(page), bm25_normalized=0.5,
    )


def _simple_tree() -> SectionTree:
    root = TreeNode("doc::root", "doc", "__root__", "", 0, 0, None, page_spans=(1, 20))
    ch1 = TreeNode("doc::h1::1", "doc", "Chapter 1", "b1", 1, 1, "doc::root", page_spans=(1, 10))
    ch2 = TreeNode("doc::h1::2", "doc", "Chapter 2", "b2", 1, 1, "doc::root", page_spans=(11, 20))
    root.children = [ch1, ch2]
    return SectionTree("doc", "doc.pdf", root, 20)


def test_adjacent_same_section_added() -> None:
    # pages 5, 6, 7 all in chapter 1; select 6 → 5 and 7 should be added
    all_cands = [_cand(5), _cand(6), _cand(7)]
    selected = [_cand(6)]
    result = expand_pages(selected, all_cands)
    pages = {c.page_number for c in result}
    assert pages == {5, 6, 7}


def test_adjacent_different_section_not_added() -> None:
    # page 10 in chapter 1, page 11 in chapter 2
    all_cands = [_cand(10, "chapter 1"), _cand(11, "chapter 2")]
    selected = [_cand(10, "chapter 1")]
    result = expand_pages(selected, all_cands)
    pages = {c.page_number for c in result}
    assert 11 not in pages


def test_no_adjacent_in_pool() -> None:
    all_cands = [_cand(5)]
    selected = [_cand(5)]
    result = expand_pages(selected, all_cands)
    assert len(result) == 1


def test_result_sorted_by_page_number() -> None:
    all_cands = [_cand(3), _cand(4), _cand(5)]
    selected = [_cand(4)]
    result = expand_pages(selected, all_cands)
    pages = [c.page_number for c in result]
    assert pages == sorted(pages)


def test_no_duplicate_pages_in_result() -> None:
    all_cands = [_cand(5), _cand(6), _cand(7)]
    selected = [_cand(5), _cand(7)]  # both selected — 6 adjacent to both
    result = expand_pages(selected, all_cands)
    page_ids = [c.page_id for c in result]
    assert len(page_ids) == len(set(page_ids))


def test_already_selected_not_duplicated() -> None:
    all_cands = [_cand(5), _cand(6)]
    selected = [_cand(5), _cand(6)]  # both already selected
    result = expand_pages(selected, all_cands)
    pages = [c.page_number for c in result]
    assert pages.count(5) == 1
    assert pages.count(6) == 1


def test_expand_with_tree() -> None:
    tree = _simple_tree()
    # pages 9 and 10 in chapter 1 (1-10), page 11 in chapter 2 (11-20)
    all_cands = [
        _cand(9, "chapter 1"), _cand(10, "chapter 1"), _cand(11, "chapter 2")
    ]
    selected = [_cand(10, "chapter 1")]
    result = expand_pages(selected, all_cands, tree)
    pages = {c.page_number for c in result}
    assert 9 in pages
    assert 11 not in pages  # different tree section


def test_empty_selected_returns_empty() -> None:
    all_cands = [_cand(5), _cand(6)]
    result = expand_pages([], all_cands)
    assert result == []
