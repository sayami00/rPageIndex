import pytest
from src.cleanup.boilerplate import is_boilerplate


@pytest.mark.parametrize("text", [
    "42",
    "© 2024 Acme Corp",
    "All Rights Reserved",
    "CONFIDENTIAL",
    "Page 3 of 12",
    "page 1",
    "DRAFT",
    "Internal Use Only",
    "www.example.com",
])
def test_detects_boilerplate(text):
    assert is_boilerplate(text) is True


@pytest.mark.parametrize("text", [
    "The quick brown fox jumps over the lazy dog.",
    "Section 2.1 Overview of System Architecture",
    "Results indicate a 15% improvement in throughput.",
    "This report summarizes findings from Q3 2024.",
])
def test_passes_normal_content(text):
    assert is_boilerplate(text) is False
