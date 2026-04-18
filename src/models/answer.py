from __future__ import annotations
from pydantic import BaseModel, field_validator, model_validator


_CITATION_STATUSES = {"VALID", "HALLUCINATED", "OUT_OF_SCOPE"}
_ANSWER_STATUSES = {"answered", "not_found"}


class RawAnswer(BaseModel):
    answer_text: str
    answer_body: str
    raw_citations: list[str]
    model_used: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    token_budget_hit: bool

    def __repr__(self) -> str:
        return (
            f"RawAnswer(model={self.model_used!r}, citations={len(self.raw_citations)}, "
            f"in={self.input_tokens}, out={self.output_tokens}, latency={self.latency_ms}ms)"
        )


class CitationResult(BaseModel):
    raw_citation: str
    source_file: str
    page_number: int
    status: str

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in _CITATION_STATUSES:
            raise ValueError(f"status must be one of {_CITATION_STATUSES}, got '{v}'")
        return v

    @field_validator("page_number")
    @classmethod
    def page_number_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"page_number must be >= 1, got {v}")
        return v

    def __repr__(self) -> str:
        return f"CitationResult(file={self.source_file!r}, page={self.page_number}, status={self.status!r})"


class VerifiedAnswer(BaseModel):
    answer: str
    status: str
    citations: list[CitationResult]
    valid_citation_count: int
    invalid_citation_count: int
    all_citations_valid: bool
    disclaimer_appended: bool
    query_original: str
    query_type: str
    latency_ms_total: int

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in _ANSWER_STATUSES:
            raise ValueError(f"status must be one of {_ANSWER_STATUSES}, got '{v}'")
        return v

    @model_validator(mode="after")
    def enforce_citation_counts(self) -> "VerifiedAnswer":
        total = self.valid_citation_count + self.invalid_citation_count
        if total != len(self.citations):
            raise ValueError(
                f"valid_citation_count + invalid_citation_count = {total} "
                f"must equal len(citations) = {len(self.citations)}"
            )
        return self

    def __repr__(self) -> str:
        return (
            f"VerifiedAnswer(status={self.status!r}, valid={self.valid_citation_count}, "
            f"invalid={self.invalid_citation_count}, latency={self.latency_ms_total}ms)"
        )
