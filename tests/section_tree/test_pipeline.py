from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.section_tree.pipeline import SectionTreePipeline
from src.section_tree.summarizer import flatten_nodes
from tests.section_tree.conftest import make_block


def _mock_response(text: str = "Summary."):
    mock_resp = AsyncMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_resp.json = AsyncMock(return_value={"response": text})
    return mock_resp


def _mock_session(text: str = "Summary."):
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.post = MagicMock(return_value=_mock_response(text))
    return session


@pytest.fixture
def pipeline(tmp_path):
    return SectionTreePipeline(
        ollama_url="http://localhost:11434",
        model="llama3.2",
        cache_dir=str(tmp_path),
        max_concurrent=2,
    )


def _run(pipeline, blocks, total_pages=10):
    with patch("src.section_tree.summarizer.aiohttp.ClientSession", return_value=_mock_session()):
        return pipeline.run(blocks, "doc1", "f.pdf", total_pages)


def test_empty_blocks_returns_root_only(pipeline):
    tree = _run(pipeline, [])
    assert tree.root.children == []
    assert tree.doc_id == "doc1"


def test_headings_become_nodes(pipeline):
    blocks = [
        make_block("b1", "heading_1", "Chapter 1", page_number=1, sequence=0),
        make_block("b2", "heading_2", "Section 1.1", page_number=2, sequence=1),
        make_block("p1", "paragraph", "Body text", page_number=2, sequence=2),
    ]
    tree = _run(pipeline, blocks)
    nodes = flatten_nodes(tree.root)
    assert len(nodes) == 2


def test_paragraphs_ignored_for_structure(pipeline):
    blocks = [make_block("p1", "paragraph", "Only paragraphs")]
    tree = _run(pipeline, blocks)
    assert tree.root.children == []


def test_summaries_populated(pipeline):
    blocks = [
        make_block("b1", "heading_1", "Title", page_number=1, sequence=0),
        make_block("p1", "paragraph", "Some body.", page_number=1, sequence=1),
    ]
    tree = _run(pipeline, blocks)
    nodes = flatten_nodes(tree.root)
    assert all(n.summary != "" for n in nodes)


def test_multi_doc_isolation(tmp_path):
    p1 = SectionTreePipeline(cache_dir=str(tmp_path))
    p2 = SectionTreePipeline(cache_dir=str(tmp_path))
    blocks_doc1 = [make_block("b1", "heading_1", "Doc1 Title", doc_id="doc1", page_number=1, sequence=0)]
    blocks_doc2 = [make_block("b2", "heading_1", "Doc2 Title", doc_id="doc2", page_number=1, sequence=0)]

    with patch("src.section_tree.summarizer.aiohttp.ClientSession", return_value=_mock_session()):
        tree1 = p1.run(blocks_doc1, "doc1", "a.pdf", 5)
        tree2 = p2.run(blocks_doc2, "doc2", "b.pdf", 5)

    nodes1 = flatten_nodes(tree1.root)
    nodes2 = flatten_nodes(tree2.root)
    assert nodes1[0].title == "Doc1 Title"
    assert nodes2[0].title == "Doc2 Title"
    assert nodes1[0].doc_id == "doc1"
    assert nodes2[0].doc_id == "doc2"


def test_tree_total_pages_set(pipeline):
    tree = _run(pipeline, [], total_pages=42)
    assert tree.total_pages == 42
