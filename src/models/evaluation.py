from __future__ import annotations
from pydantic import BaseModel


class QAPair(BaseModel):
    qa_id: str
    doc_id: str
    source_file: str
    evidence_page: int
    question: str
    answer: str
    query_type: str
    generated_by: str
    manually_reviewed: bool = False

    def __repr__(self) -> str:
        return (
            f"QAPair(qa_id={self.qa_id!r}, type={self.query_type!r}, "
            f"page={self.evidence_page}, reviewed={self.manually_reviewed})"
        )
