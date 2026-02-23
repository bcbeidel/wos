"""URL reachability checker — HTTP HEAD with GET fallback.

Lightweight module for checking whether URLs are reachable.
Uses HEAD requests with a GET fallback when HEAD returns 405.
Used by validators to verify source URL reachability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests


@dataclass
class UrlCheckResult:
    """Result of checking a single URL's reachability."""

    url: str
    status: int
    reachable: bool
    reason: Optional[str] = None


_HEADERS = {"User-Agent": "wos-url-checker/1.0"}
_TIMEOUT = 10


def check_url(url: str) -> UrlCheckResult:
    """Check whether a URL is reachable via HTTP HEAD (GET fallback on 405).

    - Non-HTTP URLs (ftp://, etc.) return reachable=False immediately.
    - HTTP HEAD request with 10s timeout.
    - If HEAD returns 405, falls back to GET with stream=True.
    - 2xx/3xx = reachable, 4xx/5xx = unreachable.
    - Connection errors / timeouts return status=0, reachable=False.
    """
    # Reject non-HTTP schemes
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return UrlCheckResult(
            url=url,
            status=0,
            reachable=False,
            reason=f"Unsupported scheme {parsed.scheme!r}: only http/https supported",
        )

    # Try HEAD first
    try:
        resp = requests.head(url, timeout=_TIMEOUT, headers=_HEADERS)
    except requests.ConnectionError as exc:
        return UrlCheckResult(
            url=url, status=0, reachable=False, reason=str(exc)
        )
    except requests.Timeout as exc:
        return UrlCheckResult(
            url=url, status=0, reachable=False, reason=str(exc)
        )
    except requests.RequestException as exc:
        return UrlCheckResult(
            url=url, status=0, reachable=False, reason=str(exc)
        )

    # HEAD returned 405 — retry with GET (stream to avoid downloading body)
    if resp.status_code == 405:
        try:
            resp = requests.get(
                url, timeout=_TIMEOUT, stream=True, headers=_HEADERS
            )
        except requests.RequestException as exc:
            return UrlCheckResult(
                url=url, status=0, reachable=False, reason=str(exc)
            )

    status = resp.status_code

    # 2xx and 3xx are reachable
    if 200 <= status < 400:
        return UrlCheckResult(url=url, status=status, reachable=True)

    # 4xx and 5xx are unreachable
    return UrlCheckResult(
        url=url,
        status=status,
        reachable=False,
        reason=f"HTTP {status}",
    )


def check_urls(urls: list) -> list:
    """Check multiple URLs for reachability, deduplicating.

    Each unique URL is checked only once. Returns one UrlCheckResult
    per unique URL. Empty input returns an empty list.
    """
    if not urls:
        return []

    seen: set = set()
    results: list = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        results.append(check_url(url))
    return results
