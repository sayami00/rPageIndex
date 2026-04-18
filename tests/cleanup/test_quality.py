import pytest
from src.cleanup.quality import compute_quality_score, compute_gate_status


def test_clean_text_scores_high():
    text = "The system architecture consists of three main components that work together to provide reliable service."
    score = compute_quality_score(text, is_boilerplate=False)
    assert score > 0.65, f"Expected PASS, got {score}"


def test_boilerplate_reduces_score():
    text = "The system architecture consists of three main components that work together to provide reliable service."
    score_normal = compute_quality_score(text, is_boilerplate=False)
    score_boiler = compute_quality_score(text, is_boilerplate=True)
    assert score_boiler < score_normal


def test_junk_text_scores_low():
    text = "\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd"
    score = compute_quality_score(text, is_boilerplate=False)
    assert score < 0.40, f"Expected REJECT, got {score}"


def test_normal_punctuation_not_counted_as_junk():
    # Commas, periods, semicolons should not reduce score
    text = "Results: accuracy 95.3%, precision 92.1%, recall 88.7%; F1 score 90.4%."
    score = compute_quality_score(text, is_boilerplate=False)
    assert score > 0.40


def test_dash_runs_counted_as_junk():
    text = "---- separator ---- another ----"
    score_with_dashes = compute_quality_score(text, is_boilerplate=False)
    score_clean = compute_quality_score("separator another clean", is_boilerplate=False)
    assert score_with_dashes <= score_clean


def test_empty_text_scores_zero():
    assert compute_quality_score("", is_boilerplate=False) == 0.0


def test_gate_status_reject():
    assert compute_gate_status(0.39) == "REJECT"
    assert compute_gate_status(0.0) == "REJECT"


def test_gate_status_flag():
    assert compute_gate_status(0.40) == "FLAG"
    assert compute_gate_status(0.65) == "FLAG"
    assert compute_gate_status(0.52) == "FLAG"


def test_gate_status_pass():
    assert compute_gate_status(0.66) == "PASS"
    assert compute_gate_status(1.0) == "PASS"


def test_score_clamped_between_0_and_1():
    score = compute_quality_score("x" * 1000, is_boilerplate=False)
    assert 0.0 <= score <= 1.0
