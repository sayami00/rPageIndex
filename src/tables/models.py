from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TableOutput:
    table_id: str
    source_pages: list[int]
    headers: list[str]
    structured: list[dict]
    search_rows: list[str]
    continuation_of: str | None = None
    continuation_group_id: str | None = None
    doc_id: str = ""

    def to_dict(self) -> dict:
        return {
            "table_id": self.table_id,
            "doc_id": self.doc_id,
            "source_pages": self.source_pages,
            "headers": self.headers,
            "structured": self.structured,
            "search_rows": self.search_rows,
            "continuation_of": self.continuation_of,
            "continuation_group_id": self.continuation_group_id,
        }
