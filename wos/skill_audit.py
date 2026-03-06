"""Skill size auditing — measure instruction density of skill files.

Provides functions to strip frontmatter, count instruction lines, and
check skill directories for size thresholds.
"""

from __future__ import annotations


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- delimited) from text.

    If text starts with ``---``, finds the next ``---`` after position 3
    and returns everything after it.  If no closing delimiter is found,
    returns the text unchanged.
    """
    if not text.startswith("---"):
        return text
    close = text.find("---", 3)
    if close == -1:
        return text
    # Skip past the closing --- and the newline that follows it
    after = close + 3
    if after < len(text) and text[after] == "\n":
        after += 1
    return text[after:]


def count_instruction_lines(text: str) -> int:
    """Count non-empty, non-structural lines in markdown text.

    Excludes blank lines, headers, code fences, table separators,
    and horizontal rules.  Everything else counts (bullets, prose,
    table data rows, numbered steps, code inside fences).
    """
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("```"):
            continue
        if stripped.startswith("|") and set(stripped) <= set("|-: "):
            continue
        if set(stripped) <= set("-* _"):
            continue
        count += 1
    return count
