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
