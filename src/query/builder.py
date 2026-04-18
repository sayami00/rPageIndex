from __future__ import annotations

from src.query.models import ExtractedEntity

_ENTITY_BOOSTS: dict[str, float] = {
    "ip":       2.0,
    "hostname": 2.0,
    "version":  1.5,
    "node":     1.5,
}


def build_bm25_query(
    token_expansions: list[tuple[str, list[str]]],
    entities: list[ExtractedEntity],
    entity_boost: float | None = None,   # None = use per-type defaults
) -> str:
    """
    Build a Whoosh query string combining synonym OR groups and boosted entity terms.

    Output format:
      (fw OR firewall) (config OR configuration) "192.168.1.1"^2.0
    """
    parts: list[str] = []

    # Synonym OR groups
    for original, expansions in token_expansions:
        if not expansions:
            parts.append(original)
        else:
            all_terms = _dedupe([original] + expansions)
            if len(all_terms) == 1:
                parts.append(all_terms[0])
            else:
                parts.append(f"({' OR '.join(all_terms)})")

    # Entity terms with boost
    for ent in entities:
        boost = entity_boost if entity_boost is not None else _ENTITY_BOOSTS.get(ent.entity_type, 1.0)
        escaped = _escape(ent.value)
        if " " in ent.value:
            parts.append(f'"{escaped}"^{boost:.1f}')
        else:
            parts.append(f'"{escaped}"^{boost:.1f}')

    return " ".join(parts)


def _escape(value: str) -> str:
    """Escape Whoosh special chars inside quoted strings (backslash-escape quotes)."""
    return value.replace('"', '\\"')


def _dedupe(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for t in terms:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            result.append(t)
    return result
