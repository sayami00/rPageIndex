from __future__ import annotations

import logging
import os
import re
import time

from src.models.answer import CitationResult, RawAnswer, VerifiedAnswer
from src.models.query import Evidence

_log = logging.getLogger(__name__)

_CITATION_LINE_RE = re.compile(r"\[file:\s*(.+?),\s*page:\s*(\d+)\]")

_NOT_FOUND_PHRASES = [
    "not in the provided documents",
    "not found in the context",
    "cannot find",
    "no information",
]


def _parse_raw_citation(raw: str) -> tuple[str, int] | None:
    m = _CITATION_LINE_RE.search(raw)
    if not m:
        return None
    filename = os.path.basename(m.group(1).strip())
    page = int(m.group(2))
    return (filename, page)


def _build_evidence_set(evidence: Evidence) -> set[tuple[str, int]]:
    return {
        (os.path.basename(p.source_file), p.page_number)
        for p in evidence.pages
    }


class CitationVerifier:
    def __init__(self, page_store: set[tuple[str, int]]) -> None:
        self._page_store = page_store

    def verify(
        self,
        raw_answer: RawAnswer,
        evidence: Evidence,
        query: str,
        query_type: str,
    ) -> VerifiedAnswer:
        t0 = time.monotonic()

        _log.info(
            "verify query_type=%s raw_citations=%d",
            query_type,
            len(raw_answer.raw_citations),
        )

        evidence_pages = _build_evidence_set(evidence)
        citation_results: list[CitationResult] = []

        for raw in raw_answer.raw_citations:
            parsed = _parse_raw_citation(raw)
            if parsed is None:
                continue
            filename, page_number = parsed

            if (filename, page_number) not in self._page_store:
                status = "HALLUCINATED"
                _log.warning(
                    "citation HALLUCINATED file=%s page=%d (not in corpus)",
                    filename,
                    page_number,
                )
            elif (filename, page_number) not in evidence_pages:
                status = "OUT_OF_SCOPE"
                _log.info(
                    "citation OUT_OF_SCOPE file=%s page=%d (not in evidence)",
                    filename,
                    page_number,
                )
            else:
                status = "VALID"
                _log.info("citation VALID file=%s page=%d", filename, page_number)

            citation_results.append(
                CitationResult(
                    raw_citation=raw,
                    source_file=filename,
                    page_number=page_number,
                    status=status,
                )
            )

        valid = [c for c in citation_results if c.status == "VALID"]
        invalid = [c for c in citation_results if c.status != "VALID"]
        valid_count = len(valid)
        invalid_count = len(invalid)
        all_valid = len(citation_results) > 0 and invalid_count == 0
        disclaimer = False

        answer_body = raw_answer.answer_body

        if valid:
            lines = "\n".join(
                f"- [file: {c.source_file}, page: {c.page_number}]" for c in valid
            )
            rebuilt = f"{answer_body}\n\nCITATIONS:\n{lines}"
        elif citation_results:
            # citations present but all invalid
            rebuilt = (
                f"{answer_body}\n\nNote: no source pages could be verified for this answer."
            )
            disclaimer = True
            _log.warning("all_citations_invalid query=%r escalating to review log", query)
        else:
            # no citations in the raw answer
            rebuilt = answer_body

        answer_status = (
            "not_found"
            if any(phrase in answer_body.lower() for phrase in _NOT_FOUND_PHRASES)
            else "answered"
        )

        verification_ms = int((time.monotonic() - t0) * 1000)
        latency_total = raw_answer.latency_ms + verification_ms

        _log.info(
            "result valid=%d hallucinated=%d out_of_scope=%d disclaimer=%s",
            valid_count,
            sum(1 for c in citation_results if c.status == "HALLUCINATED"),
            sum(1 for c in citation_results if c.status == "OUT_OF_SCOPE"),
            disclaimer,
        )

        return VerifiedAnswer(
            answer=rebuilt,
            status=answer_status,
            citations=citation_results,
            valid_citation_count=valid_count,
            invalid_citation_count=invalid_count,
            all_citations_valid=all_valid,
            disclaimer_appended=disclaimer,
            query_original=query,
            query_type=query_type,
            latency_ms_total=latency_total,
        )
