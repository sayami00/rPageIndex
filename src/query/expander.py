from __future__ import annotations

import re

_SPLIT_RE = re.compile(r"\s+")

_STOPWORDS = frozenset({
    "for", "the", "in", "at", "of", "a", "an", "is", "on",
    "to", "and", "or", "not", "with", "by", "from", "show",
    "get", "find", "list", "what", "how", "where", "which",
    "all", "any", "do", "does",
})


def tokenize(text: str) -> list[str]:
    """Split on whitespace, filter empty strings."""
    return [t for t in _SPLIT_RE.split(text) if t]


def expand_tokens(
    tokens: list[str],
    synonyms: dict[str, list[str]],
    stopwords: frozenset[str] = _STOPWORDS,
) -> list[tuple[str, list[str]]]:
    """
    Return list of (original_token, [additional_expansions]) pairs.

    - Tokens in stopwords AND without a synonym entry are dropped (empty pair list).
    - Tokens with synonym entries are never dropped even if in stopwords.
    - Tokens with no synonyms get empty expansion list.
    """
    result: list[tuple[str, list[str]]] = []
    for token in tokens:
        key = token.lower()
        expansions = synonyms.get(key, [])
        if not expansions and key in stopwords:
            continue  # drop pure stopword
        result.append((token, expansions))
    return result


def flat_terms(token_expansions: list[tuple[str, list[str]]]) -> list[str]:
    """Flat deduplicated list of all terms (originals + expansions)."""
    seen: set[str] = set()
    terms: list[str] = []
    for original, expansions in token_expansions:
        for t in [original] + expansions:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl)
                terms.append(t)
    return terms
