"""HTML parser tests — builds HTML strings and writes to temp files."""
from __future__ import annotations

import pytest
from pathlib import Path

pytest.importorskip("bs4")

from src.ingestion.html_parser import HTMLParser


def _write_html(tmp_path, content: str, name: str = "test.html") -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_html_sections_as_pages(tmp_path):
    html = """<html><body>
    <section><h1>Section One</h1><p>Content one.</p></section>
    <section><h2>Section Two</h2><p>Content two.</p></section>
    <section><h3>Section Three</h3><p>Content three.</p></section>
    </body></html>"""
    path = _write_html(tmp_path, html)
    blocks = HTMLParser().parse(path)
    page_nums = sorted(set(b.page_number for b in blocks))
    assert page_nums == [1, 2, 3]


def test_html_nav_stripped(tmp_path):
    html = """<html><body>
    <nav><a href="/">Home</a><a href="/about">About</a></nav>
    <section><p>Real content here.</p></section>
    </body></html>"""
    path = _write_html(tmp_path, html)
    blocks = HTMLParser().parse(path)
    all_text = " ".join(b.raw_text for b in blocks)
    assert "Home" not in all_text
    assert "About" not in all_text
    assert "Real content" in all_text


def test_html_headings_typed(tmp_path):
    html = """<html><body>
    <section>
        <h1>Top heading</h1>
        <h2>Sub heading</h2>
        <h3>Sub-sub heading</h3>
        <p>Body paragraph.</p>
    </section>
    </body></html>"""
    path = _write_html(tmp_path, html)
    blocks = HTMLParser().parse(path)
    hints = {b.raw_text: b.block_type_hint for b in blocks}
    assert hints.get("Top heading") == "heading_1"
    assert hints.get("Sub heading") == "heading_2"
    assert hints.get("Sub-sub heading") == "heading_3"
    assert hints.get("Body paragraph.") == "paragraph"


def test_html_table_extraction(tmp_path):
    html = """<html><body>
    <section>
        <table>
            <tr><th>Name</th><th>Age</th></tr>
            <tr><td>Alice</td><td>30</td></tr>
            <tr><td>Bob</td><td>25</td></tr>
        </table>
    </section>
    </body></html>"""
    path = _write_html(tmp_path, html)
    blocks = HTMLParser().parse(path)
    table_blocks = [b for b in blocks if b.block_type_hint == "table"]
    assert len(table_blocks) == 1
    tb = table_blocks[0]
    assert tb.raw_headers == ["Name", "Age"]
    assert len(tb.raw_rows) == 2


def test_html_hr_fallback_sections(tmp_path):
    html = """<html><body>
    <p>Part one content.</p>
    <hr/>
    <p>Part two content.</p>
    <hr/>
    <p>Part three content.</p>
    </body></html>"""
    path = _write_html(tmp_path, html)
    blocks = HTMLParser().parse(path)
    page_nums = sorted(set(b.page_number for b in blocks))
    assert len(page_nums) == 3
