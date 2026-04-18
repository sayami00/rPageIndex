from __future__ import annotations

import re

from src.query.builder import build_bm25_query
from src.query.entity_extractor import extract_entities
from src.query.expander import expand_tokens, flat_terms, tokenize
from src.query.models import ExtractedEntity, RewrittenQuery
from src.query.normalizer import normalize
from src.query.synonyms import SYNONYMS

_SPACES_RE = re.compile(r"\s+")


class QueryRewriter:
    def __init__(self, synonyms: dict[str, list[str]] | None = None):
        self._synonyms = synonyms if synonyms is not None else SYNONYMS

    def rewrite(self, query: str) -> RewrittenQuery:
        # 1. Normalize
        normalized = normalize(query)

        # 2. Extract entities from normalized text
        entities = extract_entities(normalized)

        # 3. Remove entity spans from text → remaining tokens
        remaining = _remove_entity_spans(normalized, entities)

        # 4. Tokenize + expand synonyms
        tokens = tokenize(remaining)
        token_expansions = expand_tokens(tokens, self._synonyms)

        # 5. Flat deduplicated term list
        expanded_terms = flat_terms(token_expansions)

        # 6. Build Whoosh query string
        bm25_query = build_bm25_query(token_expansions, entities)

        return RewrittenQuery(
            original=query,
            normalized=normalized,
            entities=entities,
            expanded_terms=expanded_terms,
            bm25_query=bm25_query,
        )


def _remove_entity_spans(text: str, entities: list[ExtractedEntity]) -> str:
    """Replace entity spans with spaces so they don't get tokenized as plain terms."""
    if not entities:
        return text
    chars = list(text)
    for ent in entities:
        for i in range(ent.start, min(ent.end, len(chars))):
            chars[i] = " "
    result = "".join(chars)
    return _SPACES_RE.sub(" ", result).strip()
