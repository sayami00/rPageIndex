from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractedEntity:
    value: str          # raw matched value: "192.168.1.1", "web01", "v2.3.1"
    entity_type: str    # "ip" | "hostname" | "version" | "node"
    start: int          # char offset in normalized query
    end: int


@dataclass
class RewrittenQuery:
    original: str
    normalized: str
    entities: list[ExtractedEntity]
    expanded_terms: list[str]    # all query tokens after expansion, flat, deduped
    bm25_query: str              # ready-to-use Whoosh query string


@dataclass
class ClassifiedQuery:
    original: str
    query_type: str      # "table_query" | "find_all" | "section_lookup" | "page_lookup"
    target_index: str    # "table_index" | "feature_index" | "section_index" | "page_index"
    matched_priority: int  # 1–6; 6 = default
    matched_rule: str    # human-readable label used in logs
