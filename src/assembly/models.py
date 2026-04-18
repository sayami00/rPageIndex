from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PageRecord:
    doc_id: str
    source_file: str
    page_number: int

    # Composite text fields for BM25 page-level indexing
    heading_text: str       # all heading blocks, space-joined (all gate statuses)
    body_text: str          # all paragraph blocks (PASS + FLAG only), space-joined
    table_text: str         # search_rows from tables on this page, space-joined
    page_search_text: str   # heading_text + body_text + table_text

    # Attached metadata
    features: list = field(default_factory=list)   # list[FeatureRecord]
    tables: list = field(default_factory=list)     # list[TableOutput]

    # Quality signal
    quality_floor: float = 1.0
    block_count: int = 0
