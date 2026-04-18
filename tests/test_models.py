import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from pydantic import ValidationError

from models import (
    EmptyEvidenceError,
    RawBlock, Block,
    TableRecord, FeatureRecord, PageRecord, TreeNode,
    RewrittenQuery, Candidate, Evidence,
    RawAnswer, CitationResult, VerifiedAnswer,
    QAPair,
)


# ---------------------------------------------------------------------------
# RawBlock
# ---------------------------------------------------------------------------

def test_rawblock_instantiate():
    b = RawBlock(
        block_id="doc1_p1_b0",
        doc_id="abc123",
        source_file="spec.pdf",
        source_format="pdf",
        page_number=1,
        sequence=0,
        raw_text="This is raw text from page 1.",
        block_type_hint="text",
    )
    assert b.block_id == "doc1_p1_b0"
    assert b.page_number == 1
    assert b.ocr_confidence is None
    d = b.model_dump()
    b2 = RawBlock.model_validate(d)
    assert b2.block_id == b.block_id


def test_rawblock_invalid_page_number():
    with pytest.raises(ValidationError):
        RawBlock(block_id="x", doc_id="x", source_file="x", source_format="pdf",
                 page_number=0, sequence=0, raw_text="text", block_type_hint="text")


def test_rawblock_invalid_source_format():
    with pytest.raises(ValidationError):
        RawBlock(block_id="x", doc_id="x", source_file="x", source_format="xml",
                 page_number=1, sequence=0, raw_text="text", block_type_hint="text")


def test_rawblock_empty_raw_text():
    with pytest.raises(ValidationError):
        RawBlock(block_id="x", doc_id="x", source_file="x", source_format="pdf",
                 page_number=1, sequence=0, raw_text="", block_type_hint="text")


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

def _make_block(**overrides) -> dict:
    base = dict(
        block_id="doc1_p1_b0",
        doc_id="abc123",
        source_file="spec.pdf",
        page_number=1,
        sequence=0,
        clean_text="Clean text.",
        search_text="clean text",
        block_type="paragraph",
        quality_score=0.8,
        gate_status="PASS",
        should_index=True,
        low_confidence=False,
        is_boilerplate=False,
        is_duplicate=False,
    )
    base.update(overrides)
    return base


def test_block_pass():
    b = Block(**_make_block())
    assert b.should_index is True
    assert b.low_confidence is False
    assert b.model_dump()["gate_status"] == "PASS"


def test_block_flag():
    b = Block(**_make_block(gate_status="FLAG", should_index=True, low_confidence=True))
    assert b.low_confidence is True


def test_block_reject():
    b = Block(**_make_block(gate_status="REJECT", should_index=False, low_confidence=False, quality_score=0.2))
    assert b.should_index is False


def test_block_gate_mismatch_raises():
    with pytest.raises(ValidationError):
        Block(**_make_block(gate_status="REJECT", should_index=True, low_confidence=False, quality_score=0.2))


def test_block_quality_score_out_of_range():
    with pytest.raises(ValidationError):
        Block(**_make_block(quality_score=1.5))


def test_block_roundtrip():
    b = Block(**_make_block())
    b2 = Block.model_validate(b.model_dump())
    assert b2.block_id == b.block_id
    assert b2.quality_score == b.quality_score


# ---------------------------------------------------------------------------
# TableRecord
# ---------------------------------------------------------------------------

def _make_table(**overrides) -> dict:
    base = dict(
        table_id="doc1_p2_t0",
        doc_id="abc123",
        source_file="spec.pdf",
        source_pages=[2],
        sequence_on_page=0,
        headers=["Node", "Group", "IP1"],
        header_inferred=False,
        structured=[{"Node": "Node3", "Group": "abcd", "IP1": "1.1.13.39"}],
        row_count=1,
        search_rows=["Node Node3 Group abcd IP1 1.1.13.39"],
    )
    base.update(overrides)
    return base


def test_tablerecord_instantiate():
    t = TableRecord(**_make_table())
    assert t.row_count == 1
    assert len(t.search_rows) == 1


def test_tablerecord_row_count_mismatch():
    with pytest.raises(ValidationError):
        TableRecord(**_make_table(row_count=2))


def test_tablerecord_empty_headers():
    with pytest.raises(ValidationError):
        TableRecord(**_make_table(headers=[]))


def test_tablerecord_roundtrip():
    t = TableRecord(**_make_table())
    t2 = TableRecord.model_validate(t.model_dump())
    assert t2.table_id == t.table_id


# ---------------------------------------------------------------------------
# FeatureRecord
# ---------------------------------------------------------------------------

def test_featurerecord_heading():
    f = FeatureRecord(
        feature_id="doc1_f0",
        doc_id="abc123",
        source_file="spec.pdf",
        source_page=1,
        source_block="doc1_p1_b0",
        feature_type="heading",
        feature_text="Network Configuration",
    )
    assert f.feature_type == "heading"


def test_featurerecord_key_value_pair_valid():
    f = FeatureRecord(
        feature_id="doc1_f1",
        doc_id="abc123",
        source_file="spec.pdf",
        source_page=3,
        source_block="doc1_p3_b1",
        feature_type="key_value_pair",
        feature_text="Gateway: 10.0.0.1",
        feature_key="Gateway",
        feature_value="10.0.0.1",
    )
    assert f.feature_key == "Gateway"


def test_featurerecord_key_value_pair_missing_key():
    with pytest.raises(ValidationError):
        FeatureRecord(
            feature_id="doc1_f2",
            doc_id="abc123",
            source_file="spec.pdf",
            source_page=3,
            source_block="doc1_p3_b1",
            feature_type="key_value_pair",
            feature_text="Gateway: 10.0.0.1",
            feature_key=None,
            feature_value="10.0.0.1",
        )


def test_featurerecord_invalid_type():
    with pytest.raises(ValidationError):
        FeatureRecord(
            feature_id="x", doc_id="x", source_file="x", source_page=1,
            source_block="x", feature_type="unknown", feature_text="x",
        )


# ---------------------------------------------------------------------------
# PageRecord
# ---------------------------------------------------------------------------

def _make_page(**overrides) -> dict:
    heading = "Network Configuration"
    body = "This section describes the network setup."
    table = "Node Node3 Group abcd IP1 1.1.13.39"
    base = dict(
        page_id="abc123_p1",
        doc_id="abc123",
        source_file="spec.pdf",
        page_number=1,
        heading_text=heading,
        body_text=body,
        table_text=table,
        page_search_text=f"{heading} {body} {table}",
        quality_floor=0.75,
        has_low_confidence=False,
        table_ids=["doc1_p1_t0"],
        feature_ids=["doc1_f0"],
        block_count=3,
    )
    base.update(overrides)
    return base


def test_pagerecord_instantiate():
    p = PageRecord(**_make_page())
    assert p.page_number == 1
    assert p.truncated is False


def test_pagerecord_search_text_mismatch():
    with pytest.raises(ValidationError):
        PageRecord(**_make_page(page_search_text="wrong text"))


def test_pagerecord_quality_floor_out_of_range():
    with pytest.raises(ValidationError):
        PageRecord(**_make_page(quality_floor=1.5))


def test_pagerecord_roundtrip():
    p = PageRecord(**_make_page())
    p2 = PageRecord.model_validate(p.model_dump())
    assert p2.page_id == p.page_id
    assert p2.page_search_text == p.page_search_text


# ---------------------------------------------------------------------------
# TreeNode
# ---------------------------------------------------------------------------

def _make_treenode(**overrides) -> dict:
    base = dict(
        section_id="abc123_s1",
        doc_id="abc123",
        source_file="spec.pdf",
        title="Network Configuration",
        depth=1,
        parent_id="abc123_s0",
        children=["abc123_s2", "abc123_s3"],
        summary="Describes network topology and IP addressing.",
        page_spans=[3, 4, 5],
        first_page=3,
        last_page=5,
        summary_generated_by_llm=True,
    )
    base.update(overrides)
    return base


def test_treenode_instantiate():
    n = TreeNode(**_make_treenode())
    assert n.first_page == 3
    assert n.last_page == 5
    assert len(n.children) == 2


def test_treenode_first_last_mismatch():
    with pytest.raises(ValidationError):
        TreeNode(**_make_treenode(first_page=1))


def test_treenode_root_no_parent():
    n = TreeNode(**_make_treenode(depth=0, parent_id=None, section_id="abc123_s0"))
    assert n.parent_id is None


def test_treenode_non_root_requires_parent():
    with pytest.raises(ValidationError):
        TreeNode(**_make_treenode(depth=1, parent_id=None))


def test_treenode_empty_page_spans():
    with pytest.raises(ValidationError):
        TreeNode(**_make_treenode(page_spans=[], first_page=1, last_page=1))


def test_treenode_roundtrip():
    n = TreeNode(**_make_treenode())
    n2 = TreeNode.model_validate(n.model_dump())
    assert n2.section_id == n.section_id
    assert n2.page_spans == n.page_spans


# ---------------------------------------------------------------------------
# RewrittenQuery
# ---------------------------------------------------------------------------

def test_rewrittenquery_instantiate():
    q = RewrittenQuery(
        original="What is the IP of Node3?",
        normalized="what is the ip of node3",
        expanded_terms=["ip address", "ipv4 address"],
        entities=[{"type": "node_name", "value": "Node3"}],
        bm25_query_string="what is the ip of node3 OR Node3^3",
        query_type="table_query",
        target_index="table_index",
        matched_priority=1,
    )
    assert q.query_type == "table_query"
    assert q.matched_priority == 1


def test_rewrittenquery_invalid_priority():
    with pytest.raises(ValidationError):
        RewrittenQuery(
            original="x", normalized="x", expanded_terms=[], entities=[],
            bm25_query_string="x", query_type="page_lookup",
            target_index="page_index", matched_priority=7,
        )


def test_rewrittenquery_roundtrip():
    q = RewrittenQuery(
        original="x", normalized="x", expanded_terms=[], entities=[],
        bm25_query_string="x", query_type="find_all",
        target_index="feature_index", matched_priority=3,
    )
    q2 = RewrittenQuery.model_validate(q.model_dump())
    assert q2.query_type == q.query_type


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------

def test_candidate_pre_rerank():
    c = Candidate(
        page_id="abc123_p5",
        doc_id="abc123",
        source_file="spec.pdf",
        page_number=5,
        bm25_raw=12.4,
        bm25_normalized=0.87,
    )
    assert c.is_reranked() is False
    assert c.final_score is None


def test_candidate_post_rerank():
    c = Candidate(
        page_id="abc123_p5",
        doc_id="abc123",
        source_file="spec.pdf",
        page_number=5,
        bm25_raw=12.4,
        bm25_normalized=0.87,
        hierarchy_score=0.6,
        proximity_score=0.5,
        final_score=0.72,
    )
    assert c.is_reranked() is True


def test_candidate_bm25_normalized_out_of_range():
    with pytest.raises(ValidationError):
        Candidate(
            page_id="x", doc_id="x", source_file="x", page_number=1,
            bm25_raw=5.0, bm25_normalized=1.5,
        )


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

def _sample_page() -> PageRecord:
    heading = "Section 1"
    body = "Body text here."
    table = ""
    return PageRecord(
        page_id="abc123_p1",
        doc_id="abc123",
        source_file="spec.pdf",
        page_number=1,
        heading_text=heading,
        body_text=body,
        table_text=table,
        page_search_text=f"{heading} {body}".strip(),
        quality_floor=0.8,
        has_low_confidence=False,
        table_ids=[],
        feature_ids=[],
        block_count=2,
    )


def test_evidence_instantiate():
    e = Evidence(
        pages=[_sample_page()],
        total_tokens=120,
        token_budget=3000,
        token_budget_hit=False,
        pages_dropped=0,
        query_type="page_lookup",
    )
    assert len(e.pages) == 1
    assert e.token_budget_hit is False


def test_evidence_empty_pages_raises():
    # Pydantic wraps EmptyEvidenceError in ValidationError.
    # Verify the underlying cause is EmptyEvidenceError.
    with pytest.raises(ValidationError) as exc_info:
        Evidence(
            pages=[],
            total_tokens=0,
            token_budget=3000,
            token_budget_hit=False,
            pages_dropped=0,
            query_type="page_lookup",
        )
    assert "Ollama must not be called" in str(exc_info.value)


def test_evidence_tokens_exceed_budget():
    with pytest.raises(ValidationError):
        Evidence(
            pages=[_sample_page()],
            total_tokens=5000,
            token_budget=3000,
            token_budget_hit=True,
            pages_dropped=0,
            query_type="page_lookup",
        )


# ---------------------------------------------------------------------------
# RawAnswer
# ---------------------------------------------------------------------------

def test_rawanswer_instantiate():
    r = RawAnswer(
        answer_text="Node3 IP is 1.1.13.39.\nCITATIONS:\n- [file: spec.pdf, page: 2]",
        answer_body="Node3 IP is 1.1.13.39.",
        raw_citations=["[file: spec.pdf, page: 2]"],
        model_used="qwen:7b",
        input_tokens=320,
        output_tokens=45,
        latency_ms=1200,
        token_budget_hit=False,
    )
    assert r.model_used == "qwen:7b"
    d = r.model_dump()
    r2 = RawAnswer.model_validate(d)
    assert r2.output_tokens == r.output_tokens


# ---------------------------------------------------------------------------
# CitationResult
# ---------------------------------------------------------------------------

def test_citationresult_valid():
    c = CitationResult(
        raw_citation="[file: spec.pdf, page: 2]",
        source_file="spec.pdf",
        page_number=2,
        status="VALID",
    )
    assert c.status == "VALID"


def test_citationresult_hallucinated():
    c = CitationResult(
        raw_citation="[file: spec.pdf, page: 99]",
        source_file="spec.pdf",
        page_number=99,
        status="HALLUCINATED",
    )
    assert c.status == "HALLUCINATED"


def test_citationresult_invalid_status():
    with pytest.raises(ValidationError):
        CitationResult(
            raw_citation="x", source_file="x", page_number=1, status="WRONG",
        )


def test_citationresult_invalid_page():
    with pytest.raises(ValidationError):
        CitationResult(
            raw_citation="x", source_file="x", page_number=0, status="VALID",
        )


# ---------------------------------------------------------------------------
# VerifiedAnswer
# ---------------------------------------------------------------------------

def test_verifiedanswer_instantiate():
    citations = [
        CitationResult(raw_citation="[file: spec.pdf, page: 2]",
                       source_file="spec.pdf", page_number=2, status="VALID"),
        CitationResult(raw_citation="[file: spec.pdf, page: 99]",
                       source_file="spec.pdf", page_number=99, status="HALLUCINATED"),
    ]
    va = VerifiedAnswer(
        answer="Node3 IP is 1.1.13.39.",
        status="answered",
        citations=citations,
        valid_citation_count=1,
        invalid_citation_count=1,
        all_citations_valid=False,
        disclaimer_appended=False,
        query_original="What is the IP of Node3?",
        query_type="table_query",
        latency_ms_total=1850,
    )
    assert va.valid_citation_count == 1
    assert va.all_citations_valid is False


def test_verifiedanswer_count_mismatch():
    citations = [
        CitationResult(raw_citation="x", source_file="x", page_number=1, status="VALID"),
    ]
    with pytest.raises(ValidationError):
        VerifiedAnswer(
            answer="x", status="answered", citations=citations,
            valid_citation_count=2, invalid_citation_count=0,
            all_citations_valid=True, disclaimer_appended=False,
            query_original="x", query_type="page_lookup", latency_ms_total=100,
        )


def test_verifiedanswer_roundtrip():
    citations = [
        CitationResult(raw_citation="[file: spec.pdf, page: 2]",
                       source_file="spec.pdf", page_number=2, status="VALID"),
    ]
    va = VerifiedAnswer(
        answer="Answer here.",
        status="answered",
        citations=citations,
        valid_citation_count=1,
        invalid_citation_count=0,
        all_citations_valid=True,
        disclaimer_appended=False,
        query_original="original query",
        query_type="page_lookup",
        latency_ms_total=900,
    )
    va2 = VerifiedAnswer.model_validate(va.model_dump())
    assert va2.answer == va.answer
    assert va2.citations[0].status == "VALID"


# ---------------------------------------------------------------------------
# QAPair
# ---------------------------------------------------------------------------

def test_qapair_instantiate():
    qa = QAPair(
        qa_id="abc123_qa0",
        doc_id="abc123",
        source_file="spec.pdf",
        evidence_page=2,
        question="What is the IP address of Node3?",
        answer="1.1.13.39",
        query_type="table_query",
        generated_by="qwen:7b",
    )
    assert qa.manually_reviewed is False


def test_qapair_roundtrip():
    qa = QAPair(
        qa_id="abc123_qa0",
        doc_id="abc123",
        source_file="spec.pdf",
        evidence_page=2,
        question="What is the IP address of Node3?",
        answer="1.1.13.39",
        query_type="table_query",
        generated_by="qwen:7b",
        manually_reviewed=True,
    )
    import json
    j = json.dumps(qa.model_dump())
    qa2 = QAPair.model_validate(json.loads(j))
    assert qa2.qa_id == qa.qa_id
    assert qa2.manually_reviewed is True
    assert qa2.answer == "1.1.13.39"
