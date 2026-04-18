from src.query.expander import expand_tokens, flat_terms, tokenize
from src.query.synonyms import SYNONYMS


def test_tokenize_basic():
    assert tokenize("fw config") == ["fw", "config"]


def test_tokenize_extra_spaces():
    assert tokenize("a  b   c") == ["a", "b", "c"]


def test_tokenize_empty():
    assert tokenize("") == []


def test_expand_known_abbrev():
    result = expand_tokens(["fw"], SYNONYMS)
    assert len(result) == 1
    orig, expansions = result[0]
    assert orig == "fw"
    assert "firewall" in expansions


def test_expand_unknown_token():
    result = expand_tokens(["firewall"], SYNONYMS)
    assert result == [("firewall", [])]


def test_stopword_dropped():
    result = expand_tokens(["for", "the", "firewall"], SYNONYMS)
    tokens_kept = [r[0] for r in result]
    assert "for" not in tokens_kept
    assert "the" not in tokens_kept
    assert "firewall" in tokens_kept


def test_synonym_overrides_stopword():
    # "mon" is in SYNONYMS and might be a stopword-like word; should NOT be dropped
    result = expand_tokens(["mon"], SYNONYMS)
    assert any(r[0] == "mon" for r in result)


def test_flat_terms_deduped():
    expansions = [("fw", ["firewall"]), ("config", ["configuration"])]
    terms = flat_terms(expansions)
    assert "fw" in terms
    assert "firewall" in terms
    assert "config" in terms
    assert "configuration" in terms
    assert len(terms) == len(set(t.lower() for t in terms))


def test_flat_terms_no_dup_case():
    # "Firewall" and "firewall" should not both appear
    expansions = [("Firewall", ["firewall"])]
    terms = flat_terms(expansions)
    lower_terms = [t.lower() for t in terms]
    assert lower_terms.count("firewall") == 1


def test_expand_multi_expansion():
    result = expand_tokens(["auth"], SYNONYMS)
    _, exps = result[0]
    assert len(exps) >= 2  # auth → authentication, authorization
