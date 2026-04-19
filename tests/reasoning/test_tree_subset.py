from __future__ import annotations

import pytest

from src.models.query import Candidate
from src.reasoning.tree_subset import build_tree_subset
from src.section_tree.models import SectionTree, TreeNode


def _make_tree() -> SectionTree:
    root = TreeNode("doc::root", "doc", "__root__", "", 0, 0, None, page_spans=(1, 30))
    ch1 = TreeNode("doc::h1::1", "doc", "Introduction", "b1", 1, 1, "doc::root", page_spans=(1, 5))
    ch2 = TreeNode("doc::h1::2", "doc", "Caching", "b2", 1, 1, "doc::root", page_spans=(6, 15))
    ch2_1 = TreeNode("doc::h2::3", "doc", "Memory Cache", "b3", 2, 2, "doc::h1::2", page_spans=(6, 10))
    ch2_2 = TreeNode("doc::h2::4", "doc", "Disk Cache", "b4", 2, 2, "doc::h1::2", page_spans=(11, 15))
    ch3 = TreeNode("doc::h1::5", "doc", "Advanced", "b5", 1, 1, "doc::root", page_spans=(16, 30))

    root.children = [ch1, ch2, ch3]
    ch2.children = [ch2_1, ch2_2]
    return SectionTree("doc", "doc.pdf", root, 30)


def _cand(page: int) -> Candidate:
    return Candidate(
        page_id=f"doc::p{page}", doc_id="doc", source_file="doc.pdf",
        page_number=page, bm25_raw=1.0, bm25_normalized=1.0,
    )


tree = _make_tree()


def test_returns_nodes_containing_candidate_pages() -> None:
    result = build_tree_subset([_cand(7), _cand(12)], tree)
    node_ids = {n.node_id for n in result}
    # page 7 → ch2 (6-15) + ch2_1 (6-10)
    # page 12 → ch2 (6-15) + ch2_2 (11-15)
    assert "doc::h1::2" in node_ids   # Caching
    assert "doc::h2::3" in node_ids   # Memory Cache
    assert "doc::h2::4" in node_ids   # Disk Cache


def test_excludes_nodes_with_no_candidates() -> None:
    result = build_tree_subset([_cand(3)], tree)
    node_ids = {n.node_id for n in result}
    assert "doc::h1::1" in node_ids    # Introduction contains page 3
    assert "doc::h1::2" not in node_ids  # Caching does not
    assert "doc::h1::5" not in node_ids  # Advanced does not


def test_root_excluded() -> None:
    result = build_tree_subset([_cand(3)], tree)
    assert all(n.depth > 0 for n in result)


def test_empty_candidates_returns_empty() -> None:
    assert build_tree_subset([], tree) == []


def test_document_order_preserved() -> None:
    result = build_tree_subset([_cand(3), _cand(20)], tree)
    # ch1 (Introduction, pages 1-5) before ch3 (Advanced, 16-30)
    ids = [n.node_id for n in result]
    assert ids.index("doc::h1::1") < ids.index("doc::h1::5")
