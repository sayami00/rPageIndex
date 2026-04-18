from __future__ import annotations
from pydantic import BaseModel, field_validator, model_validator


_FEATURE_TYPES = {"heading", "bullet_item", "key_value_pair", "named_entity", "repeated_pattern"}


class TableRecord(BaseModel):
    # Identity
    table_id: str
    doc_id: str
    source_file: str

    # Location
    source_pages: list[int]
    sequence_on_page: int

    # Structure
    headers: list[str]
    header_inferred: bool
    structured: list[dict]
    row_count: int

    # Multi-page linking
    continuation_of: str | None = None
    has_continuation: bool = False

    # BM25 content
    search_rows: list[str]
    title_text: str | None = None

    @field_validator("source_pages")
    @classmethod
    def source_pages_not_empty(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("source_pages must contain at least one page number")
        return v

    @field_validator("headers")
    @classmethod
    def headers_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("headers must not be empty")
        return v

    @model_validator(mode="after")
    def enforce_row_counts(self) -> "TableRecord":
        if len(self.structured) != self.row_count:
            raise ValueError(
                f"len(structured)={len(self.structured)} must equal row_count={self.row_count}"
            )
        if len(self.search_rows) != self.row_count:
            raise ValueError(
                f"len(search_rows)={len(self.search_rows)} must equal row_count={self.row_count}"
            )
        return self

    def __repr__(self) -> str:
        return (
            f"TableRecord(table_id={self.table_id!r}, pages={self.source_pages}, "
            f"rows={self.row_count}, headers={self.headers})"
        )


class FeatureRecord(BaseModel):
    feature_id: str
    doc_id: str
    source_file: str
    source_page: int
    source_block: str

    feature_type: str
    feature_text: str
    feature_key: str | None = None
    feature_value: str | None = None

    source_section: str | None = None

    @field_validator("source_page")
    @classmethod
    def source_page_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"source_page must be >= 1, got {v}")
        return v

    @field_validator("feature_type")
    @classmethod
    def feature_type_valid(cls, v: str) -> str:
        if v not in _FEATURE_TYPES:
            raise ValueError(f"feature_type must be one of {_FEATURE_TYPES}, got '{v}'")
        return v

    @field_validator("feature_text")
    @classmethod
    def feature_text_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("feature_text must not be empty")
        return v

    @model_validator(mode="after")
    def key_value_pair_requires_both(self) -> "FeatureRecord":
        if self.feature_type == "key_value_pair":
            if not self.feature_key or not self.feature_value:
                raise ValueError(
                    "feature_key and feature_value are both required when feature_type='key_value_pair'"
                )
        return self

    def __repr__(self) -> str:
        return (
            f"FeatureRecord(feature_id={self.feature_id!r}, type={self.feature_type!r}, "
            f"page={self.source_page}, text={self.feature_text!r})"
        )


class PageRecord(BaseModel):
    # Identity
    page_id: str
    doc_id: str
    source_file: str
    page_number: int

    # Composite text fields
    heading_text: str
    body_text: str
    table_text: str
    page_search_text: str

    # Section context (populated in P7)
    section_id: str | None = None
    section_path: str | None = None

    # Quality
    quality_floor: float
    has_low_confidence: bool

    # Token budget tracking (set by P10)
    truncated: bool = False

    # Attached records
    table_ids: list[str]
    feature_ids: list[str]
    block_count: int

    @field_validator("page_number")
    @classmethod
    def page_number_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"page_number must be >= 1, got {v}")
        return v

    @field_validator("quality_floor")
    @classmethod
    def quality_floor_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"quality_floor must be 0.0–1.0, got {v}")
        return v

    @model_validator(mode="after")
    def enforce_search_text(self) -> "PageRecord":
        expected = f"{self.heading_text} {self.body_text} {self.table_text}".strip()
        if self.page_search_text != expected:
            raise ValueError(
                f"page_search_text must equal heading_text + body_text + table_text. "
                f"Expected: {expected!r}, got: {self.page_search_text!r}"
            )
        return self

    def __repr__(self) -> str:
        return (
            f"PageRecord(page_id={self.page_id!r}, page={self.page_number}, "
            f"quality_floor={self.quality_floor:.2f}, blocks={self.block_count})"
        )


class TreeNode(BaseModel):
    # Identity
    section_id: str
    doc_id: str
    source_file: str

    # Hierarchy
    title: str
    depth: int
    parent_id: str | None
    children: list[str]

    # Content
    summary: str
    page_spans: list[int]
    first_page: int
    last_page: int

    # Ollama metadata
    summary_generated_by_llm: bool

    @field_validator("depth")
    @classmethod
    def depth_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"depth must be >= 0, got {v}")
        return v

    @field_validator("page_spans")
    @classmethod
    def page_spans_not_empty(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("page_spans must not be empty")
        return v

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("summary must not be empty (use title as fallback)")
        return v

    @model_validator(mode="after")
    def enforce_tree_invariants(self) -> "TreeNode":
        if self.depth == 0 and self.parent_id is not None:
            raise ValueError("parent_id must be None when depth=0")
        if self.depth > 0 and self.parent_id is None:
            raise ValueError(f"parent_id is required when depth={self.depth}")
        expected_first = min(self.page_spans)
        expected_last = max(self.page_spans)
        if self.first_page != expected_first:
            raise ValueError(f"first_page must be min(page_spans)={expected_first}, got {self.first_page}")
        if self.last_page != expected_last:
            raise ValueError(f"last_page must be max(page_spans)={expected_last}, got {self.last_page}")
        return self

    def __repr__(self) -> str:
        return (
            f"TreeNode(section_id={self.section_id!r}, depth={self.depth}, "
            f"title={self.title!r}, pages={self.page_spans})"
        )
