"""Source URL verification — check HTTP status, extract titles, compare.

Verifies that cited source URLs are reachable and that page titles
match the cited titles. Used by the health skill to detect broken
or stale sources.
"""

from __future__ import annotations

import re


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = title.lower()
    # Replace unicode dashes (en-dash, em-dash) with spaces
    text = text.replace("\u2013", " ").replace("\u2014", " ")
    # Strip non-alphanumeric except spaces
    text = re.sub(r"[^a-z0-9 ]", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def titles_match(cited: str, page: str) -> bool:
    """Check if normalized titles match via substring containment."""
    c = normalize_title(cited)
    p = normalize_title(page)
    return c in p or p in c
