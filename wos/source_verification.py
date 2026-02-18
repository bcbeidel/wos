"""Source URL verification — check HTTP status, extract titles, compare.

Verifies that cited source URLs are reachable and that page titles
match the cited titles. Used by the health skill to detect broken
or stale sources.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Optional


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


# ── HTML title extraction ─────────────────────────────────────────


class _TitleExtractor(HTMLParser):
    """Extract <title> and first <h1> from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.title: Optional[str] = None
        self.h1: Optional[str] = None
        self._in_title = False
        self._in_h1 = False
        self._title_parts: list[str] = []
        self._h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "title" and self.title is None:
            self._in_title = True
            self._title_parts = []
        elif tag == "h1" and self.h1 is None:
            self._in_h1 = True
            self._h1_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = "".join(self._title_parts).strip()
        elif tag == "h1" and self._in_h1:
            self._in_h1 = False
            self.h1 = "".join(self._h1_parts).strip()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        elif self._in_h1:
            self._h1_parts.append(data)


def extract_page_title(html: str) -> Optional[str]:
    """Extract page title from HTML.

    Prefers <title> tag; falls back to first <h1>.
    Returns None if neither found or both are empty.
    """
    parser = _TitleExtractor()
    parser.feed(html)
    # Prefer <title> but fall back to <h1> if title is empty
    if parser.title:
        return parser.title
    if parser.h1:
        return parser.h1
    return None
