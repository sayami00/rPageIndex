from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, field_validator, model_validator


_SOURCE_FORMATS = {"pdf", "docx", "xlsx", "html", "ocr"}
_BLOCK_TYPES = {
    "heading_1", "heading_2", "heading_3",
    "paragraph", "table", "list_item",
    "caption", "page_number", "boilerplate",
}
_GATE_STATUSES = {"PASS", "FLAG", "REJECT"}


class RawBlock(BaseModel):
    # Identity
    block_id: str
    doc_id: str
    source_file: str
    source_format: str

    # Location
    page_number: int
    sequence: int

    # Content
    raw_text: str
    block_type_hint: str

    # Table-specific
    raw_headers: list[str] | None = None
    raw_rows: list[dict] | None = None

    # OCR-specific
    ocr_confidence: float | None = None

    @field_validator("page_number")
    @classmethod
    def page_number_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"page_number must be >= 1, got {v}")
        return v

    @field_validator("sequence")
    @classmethod
    def sequence_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"sequence must be >= 0, got {v}")
        return v

    @field_validator("source_format")
    @classmethod
    def source_format_valid(cls, v: str) -> str:
        if v not in _SOURCE_FORMATS:
            raise ValueError(f"source_format must be one of {_SOURCE_FORMATS}, got '{v}'")
        return v

    @field_validator("raw_text")
    @classmethod
    def raw_text_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("raw_text must not be empty")
        return v

    @field_validator("ocr_confidence")
    @classmethod
    def ocr_confidence_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(f"ocr_confidence must be 0.0–1.0, got {v}")
        return v

    def __repr__(self) -> str:
        return (
            f"RawBlock(block_id={self.block_id!r}, source_file={self.source_file!r}, "
            f"page={self.page_number}, type_hint={self.block_type_hint!r}, "
            f"text_len={len(self.raw_text)})"
        )


class Block(BaseModel):
    # Inherited from RawBlock
    block_id: str
    doc_id: str
    source_file: str
    page_number: int
    sequence: int

    # Cleaned content
    clean_text: str
    search_text: str

    # Classification
    block_type: str

    # Quality signals
    quality_score: float
    gate_status: str
    should_index: bool
    low_confidence: bool
    is_boilerplate: bool

    # Deduplication
    is_duplicate: bool
    duplicate_of: str | None = None

    @field_validator("page_number")
    @classmethod
    def page_number_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"page_number must be >= 1, got {v}")
        return v

    @field_validator("quality_score")
    @classmethod
    def quality_score_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"quality_score must be 0.0–1.0, got {v}")
        return v

    @field_validator("gate_status")
    @classmethod
    def gate_status_valid(cls, v: str) -> str:
        if v not in _GATE_STATUSES:
            raise ValueError(f"gate_status must be one of {_GATE_STATUSES}, got '{v}'")
        return v

    @field_validator("block_type")
    @classmethod
    def block_type_valid(cls, v: str) -> str:
        if v not in _BLOCK_TYPES:
            raise ValueError(f"block_type must be one of {_BLOCK_TYPES}, got '{v}'")
        return v

    @model_validator(mode="after")
    def enforce_gate_derived_fields(self) -> "Block":
        expected_should_index = self.gate_status != "REJECT"
        if self.should_index != expected_should_index:
            raise ValueError(
                f"should_index must be {expected_should_index} when gate_status='{self.gate_status}'"
            )
        expected_low_confidence = self.gate_status == "FLAG"
        if self.low_confidence != expected_low_confidence:
            raise ValueError(
                f"low_confidence must be {expected_low_confidence} when gate_status='{self.gate_status}'"
            )
        return self

    def __repr__(self) -> str:
        return (
            f"Block(block_id={self.block_id!r}, type={self.block_type!r}, "
            f"gate={self.gate_status!r}, quality={self.quality_score:.2f})"
        )
