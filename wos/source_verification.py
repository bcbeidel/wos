"""Source URL verification — check HTTP status, extract titles, compare.

Verifies that cited source URLs are reachable and that page titles
match the cited titles. Used by the health skill to detect broken
or stale sources.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import requests


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


# ── Verification result ───────────────────────────────────────────


@dataclass
class VerificationResult:
    """Result of verifying a single source URL."""

    url: str
    cited_title: str
    http_status: Optional[int]
    page_title: Optional[str]
    title_match: Optional[bool]
    action: str  # "ok" | "removed" | "flagged"
    reason: str


# ── Single-source verification ────────────────────────────────────


def verify_source(url: str, cited_title: str) -> VerificationResult:
    """Verify a single source URL.

    Checks HTTP status, detects cross-domain redirects, extracts
    page title, and compares to the cited title.
    """
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True)
    except requests.ConnectionError:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=None,
            page_title=None,
            title_match=None,
            action="removed",
            reason="Connection error: could not reach URL",
        )
    except requests.Timeout:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=None,
            page_title=None,
            title_match=None,
            action="removed",
            reason="Timeout: request did not complete in time",
        )

    status = resp.status_code

    # 404 and other 4xx (except 403) → removed
    if status == 404:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=status,
            page_title=None,
            title_match=None,
            action="removed",
            reason="HTTP 404: page not found",
        )

    if status == 403:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=status,
            page_title=None,
            title_match=None,
            action="flagged",
            reason="HTTP 403: possible paywall or access restriction",
        )

    if 500 <= status < 600:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=status,
            page_title=None,
            title_match=None,
            action="flagged",
            reason=f"HTTP {status}: server error",
        )

    if 400 <= status < 500:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=status,
            page_title=None,
            title_match=None,
            action="removed",
            reason=f"HTTP {status}: client error",
        )

    # Check for cross-domain redirect
    original_domain = urlparse(url).netloc
    final_domain = urlparse(resp.url).netloc
    if original_domain != final_domain:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=status,
            page_title=None,
            title_match=None,
            action="flagged",
            reason=f"Cross-domain redirect: {original_domain} -> {final_domain}",
        )

    # 200 — extract and compare title
    page_title = extract_page_title(resp.text)

    if page_title is None:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=status,
            page_title=None,
            title_match=None,
            action="ok",
            reason="No title found on page; cannot verify",
        )

    match = titles_match(cited_title, page_title)
    if match:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=status,
            page_title=page_title,
            title_match=True,
            action="ok",
            reason="Title matches",
        )

    return VerificationResult(
        url=url,
        cited_title=cited_title,
        http_status=status,
        page_title=page_title,
        title_match=False,
        action="flagged",
        reason=f"Title mismatch: cited '{cited_title}', found '{page_title}'",
    )


# ── Batch verification ────────────────────────────────────────────


def verify_sources(sources: list[dict]) -> list[VerificationResult]:
    """Verify a list of sources. Each dict must have 'url' and 'title' keys."""
    return [verify_source(s["url"], s["title"]) for s in sources]


def format_summary(results: list[VerificationResult]) -> dict:
    """Return summary counts: {total, ok, removed, flagged}."""
    return {
        "total": len(results),
        "ok": sum(1 for r in results if r.action == "ok"),
        "removed": sum(1 for r in results if r.action == "removed"),
        "flagged": sum(1 for r in results if r.action == "flagged"),
    }
