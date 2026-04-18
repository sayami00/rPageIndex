from __future__ import annotations

import pytest

from src.assembly.models import PageRecord
from src.features.models import FeatureRecord
from src.section_tree.models import SectionTree, TreeNode
from src.tables.models import TableOutput


def make_page_record(
    page_number: int = 1,
    doc_id: str = "doc1",
    heading_text: str = "Heading",
    body_text: str = "Body text",
    table_text: str = "",
    quality_floor: float = 0.9,
) -> PageRecord:
    return PageRecord(
        doc_id=doc_id,
        source_file=f"{doc_id}.pdf",
        page_number=page_number,
        heading_text=heading_text,
        body_text=body_text,
        table_text=table_text,
        page_search_text=f"{heading_text} {body_text} {table_text}".strip(),
        quality_floor=quality_floor,
        block_count=2,
    )


def make_tree(doc_id: str = "doc1", total_pages: int = 10) -> SectionTree:
    root = TreeNode(
        node_id=f"{doc_id}::root",
        doc_id=doc_id,
        title="__root__",
        block_id="",
        heading_level=0,
        depth=0,
        parent_id=None,
        page_spans=(1, total_pages),
    )
    h1 = TreeNode(
        node_id=f"{doc_id}::h1::b1",
        doc_id=doc_id,
        title="Introduction",
        block_id="b1",
        heading_level=1,
        depth=1,
        parent_id=root.node_id,
        page_spans=(1, 5),
        summary="Overview of the document.",
    )
    h2 = TreeNode(
        node_id=f"{doc_id}::h2::b2",
        doc_id=doc_id,
        title="Background",
        block_id="b2",
        heading_level=2,
        depth=2,
        parent_id=h1.node_id,
        page_spans=(2, 3),
        summary="Historical context.",
    )
    root.children.append(h1)
    h1.children.append(h2)
    return SectionTree(doc_id=doc_id, source_file=f"{doc_id}.pdf", root=root, total_pages=total_pages)


def make_feature_index(doc_id: str = "doc1") -> dict:
    return {
        "named_entity": [
            FeatureRecord("named_entity", "192.168.1.1", "blk1", doc_id, 1, entity_subtype="ip"),
            FeatureRecord("named_entity", "server01.example.com", "blk2", doc_id, 2, entity_subtype="hostname"),
        ],
        "key_value_pair": [
            FeatureRecord("key_value_pair", "Ubuntu 22.04", "blk3", doc_id, 3, key="OS"),
        ],
    }


def make_table(doc_id: str = "doc1") -> TableOutput:
    return TableOutput(
        table_id=f"{doc_id}_t1",
        doc_id=doc_id,
        source_pages=[4, 5],
        headers=["Host", "IP", "Status"],
        structured=[{"Host": "srv01", "IP": "10.0.0.1", "Status": "active"}],
        search_rows=["Host srv01 IP 10.0.0.1 Status active"],
    )
