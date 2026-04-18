import pytest
from src.section_tree.builder import build_tree, _flatten_nodes
from src.section_tree.detector import extract_headings
from tests.section_tree.conftest import make_block


def _headings(*specs):
    """specs: list of (block_id, block_type, page, sequence)"""
    return [
        make_block(bid, btype, f"Title {bid}", page_number=page, sequence=seq)
        for bid, btype, page, seq in specs
    ]


def test_empty_headings_returns_root_only():
    tree = build_tree([], "doc1", "f.pdf", total_pages=5)
    assert tree.root.title == "__root__"
    assert tree.root.children == []
    assert tree.root.page_spans == (1, 5)


def test_single_h1():
    headings = _headings(("b1", "heading_1", 2, 0))
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=10)
    assert len(tree.root.children) == 1
    node = tree.root.children[0]
    assert node.heading_level == 1
    assert node.depth == 1
    assert node.parent_id == tree.root.node_id
    assert node.page_spans == (2, 10)


def test_h2_becomes_child_of_h1():
    headings = _headings(
        ("b1", "heading_1", 1, 0),
        ("b2", "heading_2", 3, 1),
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=10)
    h1 = tree.root.children[0]
    assert len(h1.children) == 1
    h2 = h1.children[0]
    assert h2.heading_level == 2
    assert h2.parent_id == h1.node_id


def test_h2_before_h1_becomes_child_of_root():
    headings = _headings(
        ("b1", "heading_2", 1, 0),
        ("b2", "heading_1", 3, 1),
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=10)
    # h2 appears before any h1 — should be root child
    assert len(tree.root.children) == 2
    assert tree.root.children[0].heading_level == 2
    assert tree.root.children[1].heading_level == 1


def test_multiple_h1s_are_siblings():
    headings = _headings(
        ("b1", "heading_1", 1, 0),
        ("b2", "heading_1", 5, 1),
        ("b3", "heading_1", 9, 2),
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=12)
    assert len(tree.root.children) == 3


def test_page_spans_no_overlap():
    headings = _headings(
        ("b1", "heading_1", 1, 0),
        ("b2", "heading_1", 6, 1),
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=10)
    h1a = tree.root.children[0]
    h1b = tree.root.children[1]
    assert h1a.page_spans == (1, 5)
    assert h1b.page_spans == (6, 10)


def test_child_page_spans_within_parent():
    headings = _headings(
        ("b1", "heading_1", 1, 0),
        ("b2", "heading_2", 3, 1),
        ("b3", "heading_2", 6, 2),
        ("b4", "heading_1", 9, 3),
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=12)
    h1a = tree.root.children[0]
    h2a, h2b = h1a.children
    assert h2a.page_spans == (3, 5)
    assert h2b.page_spans == (6, 8)
    assert h1a.page_spans == (1, 8)


def test_node_ids_unique():
    headings = _headings(
        ("b1", "heading_1", 1, 0),
        ("b2", "heading_2", 2, 1),
        ("b3", "heading_3", 3, 2),
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=5)
    flat = _flatten_nodes(tree.root)
    ids = [n.node_id for n in flat]
    assert len(ids) == len(set(ids))


def test_page_spans_first_never_exceeds_last():
    headings = _headings(
        ("b1", "heading_1", 1, 0),
        ("b2", "heading_2", 1, 1),  # same page as parent
        ("b3", "heading_1", 1, 2),  # same page as siblings
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=5)
    flat = _flatten_nodes(tree.root)
    for node in flat:
        assert node.page_spans[0] <= node.page_spans[1]


def test_single_page_document():
    headings = _headings(
        ("b1", "heading_1", 1, 0),
        ("b2", "heading_2", 1, 1),
    )
    tree = build_tree(headings, "doc1", "f.pdf", total_pages=1)
    flat = _flatten_nodes(tree.root)
    for node in flat:
        assert node.page_spans == (1, 1)
