import pytest
from src.features.repeated import extract_repeated_patterns, _tokenize
from tests.features.conftest import make_block


def _make_paragraph(block_id: str, text: str, page: int = 1) -> object:
    return make_block(
        block_id=block_id,
        block_type="paragraph",
        clean_text=text,
        page_number=page,
    )


def test_token_appearing_3_times_extracted():
    blocks = [
        _make_paragraph("b1", "authentication module handles authentication requests"),
        _make_paragraph("b2", "the authentication service validates tokens"),
        _make_paragraph("b3", "authentication is required for all endpoints"),
    ]
    result = extract_repeated_patterns(blocks)
    values = {r.value for r in result}
    assert "authentication" in values


def test_token_appearing_twice_not_extracted():
    blocks = [
        _make_paragraph("b1", "encryption module encrypts data"),
        _make_paragraph("b2", "encryption keys are rotated"),
    ]
    result = extract_repeated_patterns(blocks)
    values = {r.value for r in result}
    assert "encryption" not in values


def test_skips_rejected_blocks():
    blocks = [
        make_block(block_id=f"b{i}", block_type="paragraph",
                   clean_text="authentication module here", gate_status="REJECT")
        for i in range(5)
    ]
    result = extract_repeated_patterns(blocks)
    assert result == []


def test_stopwords_not_extracted():
    # "from", "with", "that" etc. must not appear even if repeated many times
    blocks = [
        _make_paragraph(f"b{i}", "data from this system with that config")
        for i in range(5)
    ]
    result = extract_repeated_patterns(blocks)
    stopword_hits = [r for r in result if r.value in {"from", "with", "that", "this"}]
    assert stopword_hits == []


def test_frequency_field_set():
    blocks = [
        _make_paragraph(f"b{i}", "kubernetes cluster deployment")
        for i in range(4)
    ]
    result = extract_repeated_patterns(blocks)
    kube = [r for r in result if r.value == "kubernetes"]
    assert len(kube) == 1
    assert kube[0].frequency == 4


def test_short_tokens_excluded():
    # Tokens < 4 chars should not be extracted
    blocks = [_make_paragraph(f"b{i}", "big cat ran") for i in range(5)]
    result = extract_repeated_patterns(blocks)
    short = [r for r in result if len(r.value) < 4]
    assert short == []


def test_grouped_by_block_type():
    # "system" in paragraph blocks × 3 → extracted
    # "system" in heading blocks × 3 → also extracted (separate entry)
    para_blocks = [
        make_block(block_id=f"p{i}", block_type="paragraph",
                   clean_text="system performance metrics")
        for i in range(3)
    ]
    head_blocks = [
        make_block(block_id=f"h{i}", block_type="heading_1",
                   clean_text="system overview section")
        for i in range(3)
    ]
    result = extract_repeated_patterns(para_blocks + head_blocks)
    system_hits = [r for r in result if r.value == "system"]
    # At least 2 entries (one per block_type)
    assert len(system_hits) >= 2


def test_tokenize_lowercases():
    tokens = _tokenize("Authentication MODULE")
    assert "authentication" in tokens
    assert "module" in tokens


def test_tokenize_removes_stopwords():
    tokens = _tokenize("the system from that configuration")
    assert "the" not in tokens
    assert "from" not in tokens
    assert "that" not in tokens
    assert "system" in tokens
