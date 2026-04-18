from __future__ import annotations

import re

# Punctuation safe to strip — everything except domain-meaningful chars
# We keep: alphanumerics, space, dot, slash, hyphen, colon, wildcard chars ? *
_STRIP_RE = re.compile(r"[^\w\s.\-/:?*]")

# Multiple consecutive wildcards are not wildcards — strip them
_MULTI_WILDCARD_RE = re.compile(r"[?*]{2,}")

# Collapse multiple spaces
_SPACES_RE = re.compile(r"\s+")

# Dots not fully surrounded by alphanumerics on BOTH sides → strip
# Matches dot where either neighbor is non-alphanumeric
_BARE_DOT_RE = re.compile(r"(?<![a-zA-Z0-9])\.|\.(?![a-zA-Z0-9])")

# Hyphens/slashes NOT between alphanumerics → strip
_BARE_HYPHEN_RE = re.compile(r"(?<![a-zA-Z0-9])-(?![a-zA-Z0-9])")
_BARE_SLASH_RE = re.compile(r"(?<![a-zA-Z0-9])/(?![a-zA-Z0-9])")

# Bare colons (sentence punctuation) → strip colons not in "word: value" pattern
# Keep colon only when immediately followed by non-space (e.g. "http:" not "key: value")
_BARE_COLON_RE = re.compile(r":\s")


def normalize(query: str) -> str:
    """Lowercase, strip extraneous punctuation, preserve domain chars."""
    text = query.strip().lower()

    # Strip bare colons used as sentence punctuation (keep "http:" "key:value")
    text = _BARE_COLON_RE.sub(" ", text)

    # Strip repeated wildcards before other processing
    text = _MULTI_WILDCARD_RE.sub(" ", text)

    # Strip chars outside the safe set
    text = _STRIP_RE.sub(" ", text)

    # Clean up isolated punctuation
    text = _BARE_DOT_RE.sub(" ", text)
    text = _BARE_HYPHEN_RE.sub(" ", text)
    text = _BARE_SLASH_RE.sub(" ", text)

    # Collapse whitespace
    text = _SPACES_RE.sub(" ", text).strip()

    return text
