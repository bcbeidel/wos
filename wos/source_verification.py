"""Source URL verification — check HTTP status, extract titles, compare.

Verifies that cited source URLs are reachable and that page titles
match the cited titles. Used by the health skill to detect broken
or stale sources.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ConfigDict


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
    if not c or not p:
        return False
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


class VerificationResult(BaseModel):
    """Result of verifying a single source URL."""

    model_config = ConfigDict(frozen=True)

    url: str
    cited_title: str
    http_status: Optional[int]
    page_title: Optional[str]
    title_match: Optional[bool]
    action: str  # "ok" | "removed" | "flagged"
    reason: str

    def __str__(self) -> str:
        return f"{self.action}: {self.url}"

    def __repr__(self) -> str:
        return (
            f"VerificationResult(action={self.action!r}, "
            f"url={self.url!r}, reason={self.reason!r})"
        )

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> VerificationResult:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls.model_validate(data)

class ReachabilityResult(BaseModel):
    """Result of a lightweight URL reachability check."""

    model_config = ConfigDict(frozen=True)

    url: str
    http_status: Optional[int]
    reachable: bool
    reason: str
    final_url: Optional[str]

    def __str__(self) -> str:
        status = "reachable" if self.reachable else "unreachable"
        return f"{status}: {self.url}"

    def __repr__(self) -> str:
        return (
            f"ReachabilityResult(reachable={self.reachable!r}, "
            f"url={self.url!r}, reason={self.reason!r})"
        )

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> ReachabilityResult:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls.model_validate(data)


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
    except requests.RequestException as exc:
        return VerificationResult(
            url=url,
            cited_title=cited_title,
            http_status=None,
            page_title=None,
            title_match=None,
            action="flagged",
            reason=f"Request error: {exc}",
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


# ── Lightweight reachability check ────────────────────────────────


def check_url_reachability(url: str) -> ReachabilityResult:
    """Check if a URL is reachable via HTTP HEAD (GET fallback on 405).

    Lightweight alternative to verify_source() — checks reachability
    only, no title extraction or comparison.
    """
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
    except requests.ConnectionError:
        return ReachabilityResult(
            url=url, http_status=None, reachable=False,
            reason="Connection error: could not reach URL",
            final_url=None,
        )
    except requests.Timeout:
        return ReachabilityResult(
            url=url, http_status=None, reachable=False,
            reason="Timeout: request did not complete in time",
            final_url=None,
        )
    except requests.RequestException as exc:
        return ReachabilityResult(
            url=url, http_status=None, reachable=False,
            reason=f"Request error: {exc}",
            final_url=None,
        )

    status = resp.status_code

    # HEAD returned 405 — retry with GET
    if status == 405:
        try:
            resp = requests.get(url, timeout=10, allow_redirects=True)
            status = resp.status_code
        except requests.RequestException as exc:
            return ReachabilityResult(
                url=url, http_status=None, reachable=False,
                reason=f"GET fallback failed: {exc}",
                final_url=None,
            )

    final_url = resp.url

    # Cross-domain redirect detection
    original_domain = urlparse(url).netloc
    final_domain = urlparse(final_url).netloc
    if original_domain != final_domain:
        return ReachabilityResult(
            url=url, http_status=status, reachable=False,
            reason=f"Cross-domain redirect: {original_domain} -> {final_domain}",
            final_url=final_url,
        )

    if status == 200:
        return ReachabilityResult(
            url=url, http_status=200, reachable=True,
            reason="OK", final_url=final_url,
        )

    if status == 403:
        return ReachabilityResult(
            url=url, http_status=403, reachable=False,
            reason="HTTP 403: possible paywall or access restriction",
            final_url=final_url,
        )

    if status == 404:
        return ReachabilityResult(
            url=url, http_status=404, reachable=False,
            reason="HTTP 404: page not found",
            final_url=final_url,
        )

    if 500 <= status < 600:
        return ReachabilityResult(
            url=url, http_status=status, reachable=False,
            reason=f"HTTP {status}: server error",
            final_url=final_url,
        )

    if 400 <= status < 500:
        return ReachabilityResult(
            url=url, http_status=status, reachable=False,
            reason=f"HTTP {status}: client error",
            final_url=final_url,
        )

    # 2xx/3xx other than 200 — treat as reachable
    return ReachabilityResult(
        url=url, http_status=status, reachable=True,
        reason=f"HTTP {status}", final_url=final_url,
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


# ── Human-readable output ─────────────────────────────────────────

_ACTION_ICONS = {"ok": "\u2713", "removed": "\u2717", "flagged": "\u26a0"}


def format_human_summary(results: list[VerificationResult]) -> str:
    """Format results as a human-readable string with icons."""
    lines: list[str] = []
    for r in results:
        icon = _ACTION_ICONS.get(r.action, "?")
        lines.append(f"  {icon} {r.url} - {r.reason}")
    summary = format_summary(results)
    lines.append("")
    lines.append(
        f"Total: {summary['total']}  "
        f"OK: {summary['ok']}  "
        f"Removed: {summary['removed']}  "
        f"Flagged: {summary['flagged']}"
    )
    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────


def main() -> None:
    """Read JSON from stdin, verify sources, write JSON to stdout.

    Human summary goes to stderr. Exits 1 if any sources were removed.
    """
    sources = json.load(sys.stdin)
    results = verify_sources(sources)
    summary = format_summary(results)

    output = {
        "results": [r.to_json() for r in results],
        "summary": summary,
    }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")

    sys.stderr.write(format_human_summary(results))
    sys.stderr.write("\n")

    if summary["removed"] > 0:
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
