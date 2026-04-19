from __future__ import annotations
from pydantic import BaseModel, field_validator, model_validator
from .exceptions import EmptyEvidenceError
from .index import PageRecord


_QUERY_TYPES = {"page_lookup", "section_lookup", "table_query", "find_all"}
_TARGET_INDEXES = {"page_index", "section_index", "feature_index", "table_index"}


class RewrittenQuery(BaseModel):
    original: str
    normalized: str
    expanded_terms: list[str]
    entities: list[dict]
    bm25_query_string: str
    query_type: str
    target_index: str
    matched_priority: int

    @field_validator("query_type")
    @classmethod
    def query_type_valid(cls, v: str) -> str:
        if v not in _QUERY_TYPES:
            raise ValueError(f"query_type must be one of {_QUERY_TYPES}, got '{v}'")
        return v

    @field_validator("target_index")
    @classmethod
    def target_index_valid(cls, v: str) -> str:
        if v not in _TARGET_INDEXES:
            raise ValueError(f"target_index must be one of {_TARGET_INDEXES}, got '{v}'")
        return v

    @field_validator("matched_priority")
    @classmethod
    def matched_priority_range(cls, v: int) -> int:
        if not (1 <= v <= 6):
            raise ValueError(f"matched_priority must be 1–6, got {v}")
        return v

    def __repr__(self) -> str:
        return (
            f"RewrittenQuery(type={self.query_type!r}, index={self.target_index!r}, "
            f"priority={self.matched_priority}, query={self.normalized!r})"
        )


class Candidate(BaseModel):
    # Source
    page_id: str
    doc_id: str
    source_file: str
    page_number: int

    # Section context (populated from BM25 result dict when available)
    section_path: str = ""

    # BM25 scores
    bm25_raw: float
    bm25_normalized: float

    # Reranker scores (None until P9.2 runs)
    hierarchy_score: float | None = None
    proximity_score: float | None = None
    final_score: float | None = None

    # Fallback tracking
    retrieved_at_fallback_step: int = 0

    @field_validator("bm25_normalized")
    @classmethod
    def bm25_normalized_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"bm25_normalized must be 0.0–1.0, got {v}")
        return v

    @field_validator("hierarchy_score", "proximity_score", "final_score", mode="before")
    @classmethod
    def score_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(f"score must be 0.0–1.0, got {v}")
        return v

    def is_reranked(self) -> bool:
        return all(s is not None for s in (self.hierarchy_score, self.proximity_score, self.final_score))

    def __repr__(self) -> str:
        score_str = f"final={self.final_score:.3f}" if self.final_score is not None else "not_reranked"
        return (
            f"Candidate(page_id={self.page_id!r}, bm25={self.bm25_normalized:.3f}, {score_str})"
        )


class Evidence(BaseModel):
    pages: list[PageRecord]
    total_tokens: int
    token_budget: int
    token_budget_hit: bool
    pages_dropped: int
    query_type: str

    @model_validator(mode="after")
    def enforce_non_empty_pages(self) -> "Evidence":
        if not self.pages:
            raise EmptyEvidenceError(
                "Evidence.pages is empty — Ollama must not be called. "
                "Return not_found response instead."
            )
        if self.total_tokens > self.token_budget:
            raise ValueError(
                f"total_tokens={self.total_tokens} exceeds token_budget={self.token_budget}"
            )
        return self

    @field_validator("query_type")
    @classmethod
    def query_type_valid(cls, v: str) -> str:
        _QUERY_TYPES = {"page_lookup", "section_lookup", "table_query", "find_all"}
        if v not in _QUERY_TYPES:
            raise ValueError(f"query_type must be one of {_QUERY_TYPES}, got '{v}'")
        return v

    def __repr__(self) -> str:
        return (
            f"Evidence(pages={len(self.pages)}, tokens={self.total_tokens}/{self.token_budget}, "
            f"budget_hit={self.token_budget_hit}, dropped={self.pages_dropped})"
        )
