from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"[.?!\u201d\u2019][\"')]?\s*$")
_STARTS_LOWERCASE = re.compile(r"^[a-z]")


def reconstruct_paragraphs(text: str) -> str:
    """Rejoin lines broken by PDF extraction artifacts.

    Joins when: previous line has no sentence-ending punctuation
    AND next line starts with a lowercase letter.
    """
    lines = text.split("\n")
    if len(lines) <= 1:
        return text

    result: list[str] = [lines[0]]
    for line in lines[1:]:
        prev = result[-1]
        if (
            prev.strip()
            and line.strip()
            and not _SENTENCE_END.search(prev)
            and _STARTS_LOWERCASE.match(line.strip())
        ):
            result[-1] = prev.rstrip() + " " + line.strip()
        else:
            result.append(line)

    return "\n".join(result)
