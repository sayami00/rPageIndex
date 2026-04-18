from __future__ import annotations

from rapidfuzz import fuzz

SIMILARITY_THRESHOLD = 90.0
_MIN_TEXT_LEN = 20  # skip dedup check for very short texts


def mark_duplicates(intermediates: list[dict]) -> list[dict]:
    """Detect near-duplicate blocks by clean_text similarity (threshold: 90%).

    Mutates intermediates in-place: sets is_duplicate=True and duplicate_of=<block_id>
    for all duplicates. First occurrence is kept. Returns the same list.
    """
    seen: list[tuple[str, str]] = []  # (block_id, clean_text)

    for block in intermediates:
        text = block.get("clean_text", "")
        if not text or len(text) < _MIN_TEXT_LEN:
            continue

        dup_of = None
        for seen_id, seen_text in seen:
            score = fuzz.ratio(text, seen_text)
            if score >= SIMILARITY_THRESHOLD:
                dup_of = seen_id
                break

        if dup_of:
            block["is_duplicate"] = True
            block["duplicate_of"] = dup_of
        else:
            seen.append((block["block_id"], text))

    return intermediates
