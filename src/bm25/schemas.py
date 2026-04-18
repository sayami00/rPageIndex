from __future__ import annotations

from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import ID, NUMERIC, TEXT, Schema


def page_schema() -> Schema:
    return Schema(
        page_id=ID(stored=True, unique=True),          # "{doc_id}::p{page_number}"
        doc_id=ID(stored=True),
        page_number=NUMERIC(stored=True, numtype=int),
        heading_text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        body_text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        table_text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        section_path=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        quality_floor=NUMERIC(stored=True, numtype=float),
    )


def section_schema() -> Schema:
    return Schema(
        section_id=ID(stored=True, unique=True),       # TreeNode.node_id
        doc_id=ID(stored=True),
        title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        summary=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        page_span_first=NUMERIC(stored=True, numtype=int),
        page_span_last=NUMERIC(stored=True, numtype=int),
        depth=NUMERIC(stored=True, numtype=int),
        parent_id=ID(stored=True),
    )


def feature_schema() -> Schema:
    return Schema(
        feature_id=ID(stored=True, unique=True),       # "{block_id}::{type}::{value_hash}"
        doc_id=ID(stored=True),
        feature_type=ID(stored=True),
        feature_text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        feature_exact=ID(stored=True),                 # raw value, no analysis — exact match
        source_page=NUMERIC(stored=True, numtype=int),
        source_section=ID(stored=True),                # node_id of deepest enclosing section
    )


def table_schema() -> Schema:
    return Schema(
        table_id=ID(stored=True, unique=True),
        doc_id=ID(stored=True),
        source_pages=TEXT(stored=True),                # space-joined ints: "3 4 5"
        headers_text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        search_rows_text=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        continuation_of=ID(stored=True),
    )
