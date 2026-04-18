from whoosh.fields import ID, NUMERIC, TEXT

from src.bm25.schemas import feature_schema, page_schema, section_schema, table_schema


def test_page_schema_fields():
    s = page_schema()
    assert "page_id" in s.names()
    assert "doc_id" in s.names()
    assert "body_text" in s.names()
    assert "section_path" in s.names()
    assert "quality_floor" in s.names()


def test_section_schema_fields():
    s = section_schema()
    assert "section_id" in s.names()
    assert "title" in s.names()
    assert "summary" in s.names()
    assert "page_span_first" in s.names()
    assert "parent_id" in s.names()


def test_feature_schema_has_dual_fields():
    s = feature_schema()
    assert "feature_text" in s.names()    # stemmed
    assert "feature_exact" in s.names()   # raw/exact


def test_table_schema_fields():
    s = table_schema()
    assert "table_id" in s.names()
    assert "headers_text" in s.names()
    assert "search_rows_text" in s.names()
    assert "continuation_of" in s.names()


def test_unique_ids_marked():
    # ID fields with unique=True are used for update_document
    for schema_fn in (page_schema, section_schema, feature_schema, table_schema):
        s = schema_fn()
        id_fields = [name for name in s.names() if isinstance(s[name], ID)]
        assert id_fields, f"{schema_fn.__name__} has no ID fields"
