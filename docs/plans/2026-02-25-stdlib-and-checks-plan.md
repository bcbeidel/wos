---
name: Stdlib Migration and Validator Refactoring Plan
description: Step-by-step implementation plan for issue #68
type: plan
related:
  - docs/plans/2026-02-25-stdlib-and-checks-design.md
---

# Stdlib Migration & Validator Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all runtime dependencies (pyyaml, requests, pydantic), add warn/fail severity, preamble-preserving indexes, LLM-friendly output, and a new /distill skill.

**Architecture:** Three phases on a single `feat/stdlib-and-checks` branch. Phase 1 replaces external dependencies with stdlib equivalents. Phase 2 refactors validators and CLI output. Phase 3 updates skills. TDD throughout — write failing tests first, then implement.

**Tech Stack:** Python 3.9+ stdlib only (no runtime dependencies). pytest + ruff for dev.

**Branch:** `feat/stdlib-and-checks` | **PR:** [#69](https://github.com/bcbeidel/wos/pull/69) (merged) | **Release:** [v0.4.0](https://github.com/bcbeidel/wos/releases/tag/v0.4.0)

---

## Phase 1: Stdlib Migration

### ~~Task 1: Create custom frontmatter parser~~ [DONE]

**Files:**
- Create: `wos/frontmatter.py`
- Create: `tests/test_frontmatter.py`

**Step 1: Write the failing tests**

```python
"""Tests for wos/frontmatter.py — custom YAML frontmatter parser."""

from __future__ import annotations

import pytest

from wos.frontmatter import parse_frontmatter


class TestDelimiters:
    def test_valid_frontmatter_returns_dict_and_body(self) -> None:
        text = "---\nname: Test\ndescription: A test\n---\nBody content.\n"
        fm, body = parse_frontmatter(text)
        assert fm == {"name": "Test", "description": "A test"}
        assert body == "Body content.\n"

    def test_no_opening_delimiter_raises(self) -> None:
        with pytest.raises(ValueError, match="frontmatter"):
            parse_frontmatter("name: Test\n---\n")

    def test_no_closing_delimiter_raises(self) -> None:
        with pytest.raises(ValueError, match="closing"):
            parse_frontmatter("---\nname: Test\n")

    def test_empty_frontmatter_returns_empty_dict(self) -> None:
        fm, body = parse_frontmatter("---\n---\nBody.\n")
        assert fm == {}
        assert body == "Body.\n"

    def test_frontmatter_at_end_of_file_no_body(self) -> None:
        fm, body = parse_frontmatter("---\nname: Test\n---")
        assert fm == {"name": "Test"}
        assert body == ""

    def test_frontmatter_with_trailing_newline_only(self) -> None:
        fm, body = parse_frontmatter("---\nname: Test\n---\n")
        assert fm == {"name": "Test"}
        assert body == ""


class TestScalarValues:
    def test_key_value_pair(self) -> None:
        fm, _ = parse_frontmatter("---\nname: Hello World\n---\n")
        assert fm["name"] == "Hello World"

    def test_key_with_no_value_is_none(self) -> None:
        fm, _ = parse_frontmatter("---\nname: Test\ntype:\n---\n")
        assert fm["type"] is None

    def test_no_type_coercion_numbers_stay_strings(self) -> None:
        fm, _ = parse_frontmatter("---\nname: 42\ndescription: 100\n---\n")
        assert fm["name"] == "42"
        assert fm["description"] == "100"

    def test_no_type_coercion_booleans_stay_strings(self) -> None:
        fm, _ = parse_frontmatter("---\nname: true\ndescription: false\n---\n")
        assert fm["name"] == "true"
        assert fm["description"] == "false"

    def test_value_with_colon_in_it(self) -> None:
        fm, _ = parse_frontmatter("---\nname: http://example.com\n---\n")
        assert fm["name"] == "http://example.com"

    def test_value_with_leading_trailing_spaces_stripped(self) -> None:
        fm, _ = parse_frontmatter("---\nname:   Hello   \n---\n")
        assert fm["name"] == "Hello"


class TestListValues:
    def test_simple_list(self) -> None:
        text = "---\nsources:\n  - https://a.com\n  - https://b.com\n---\n"
        fm, _ = parse_frontmatter(text)
        assert fm["sources"] == ["https://a.com", "https://b.com"]

    def test_list_items_without_indent(self) -> None:
        text = "---\nsources:\n- https://a.com\n- https://b.com\n---\n"
        fm, _ = parse_frontmatter(text)
        assert fm["sources"] == ["https://a.com", "https://b.com"]

    def test_list_item_values_stripped(self) -> None:
        text = "---\nsources:\n  -   https://a.com  \n---\n"
        fm, _ = parse_frontmatter(text)
        assert fm["sources"] == ["https://a.com"]

    def test_key_with_no_value_followed_by_list(self) -> None:
        text = "---\nrelated:\n  - file1.md\n  - file2.md\n---\n"
        fm, _ = parse_frontmatter(text)
        assert fm["related"] == ["file1.md", "file2.md"]

    def test_key_with_null_and_no_list_stays_none(self) -> None:
        text = "---\nsources:\nname: Test\n---\n"
        fm, _ = parse_frontmatter(text)
        assert fm["sources"] is None
        assert fm["name"] == "Test"


class TestEdgeCases:
    def test_blank_lines_in_frontmatter_ignored(self) -> None:
        text = "---\nname: Test\n\ndescription: Desc\n---\n"
        fm, _ = parse_frontmatter(text)
        assert fm["name"] == "Test"
        assert fm["description"] == "Desc"

    def test_comment_lines_ignored(self) -> None:
        text = "---\n# This is a comment\nname: Test\n---\n"
        fm, _ = parse_frontmatter(text)
        assert fm["name"] == "Test"
        assert "#" not in fm

    def test_body_content_preserved_exactly(self) -> None:
        text = "---\nname: Test\n---\n# Heading\n\nParagraph.\n"
        _, body = parse_frontmatter(text)
        assert body == "# Heading\n\nParagraph.\n"

    def test_body_with_dashes_not_confused_for_delimiter(self) -> None:
        text = "---\nname: Test\n---\n# Heading\n\n---\n\nMore content.\n"
        _, body = parse_frontmatter(text)
        assert "---" in body
        assert "More content." in body

    def test_quoted_values_preserve_quotes(self) -> None:
        text = '---\nname: "Quoted Value"\n---\n'
        fm, _ = parse_frontmatter(text)
        # Quotes are part of the string (no YAML quoting semantics)
        assert fm["name"] == '"Quoted Value"'
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_frontmatter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wos.frontmatter'`

**Step 3: Write minimal implementation**

```python
"""Custom frontmatter parser for WOS documents.

Parses the restricted YAML subset used in WOS frontmatter:
- key: value (scalars, always strings, no type coercion)
- key: (null)
- list items under a key (- item)

No nested dicts, no booleans, no numbers, no dates.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union


def parse_frontmatter(text: str) -> Tuple[Dict[str, Union[str, List[str], None]], str]:
    """Parse YAML frontmatter from markdown text.

    Args:
        text: Raw markdown text, expected to start with '---'.

    Returns:
        Tuple of (frontmatter_dict, body_content).

    Raises:
        ValueError: If frontmatter delimiters are missing or malformed.
    """
    if not text.startswith("---\n"):
        raise ValueError("No YAML frontmatter found (file must start with '---')")

    # Find closing delimiter
    close_idx = text.find("\n---\n", 3)
    if close_idx != -1:
        yaml_region = text[4:close_idx]
        body = text[close_idx + 5:]
    else:
        close_idx = text.find("\n---", 3)
        if close_idx != -1 and close_idx + 4 >= len(text):
            yaml_region = text[4:close_idx]
            body = ""
        else:
            raise ValueError("No closing frontmatter delimiter found")

    fm = _parse_yaml_subset(yaml_region)
    return fm, body


def _parse_yaml_subset(
    yaml_text: str,
) -> Dict[str, Union[str, List[str], None]]:
    """Parse the restricted YAML subset used in frontmatter.

    Handles:
    - key: value -> {"key": "value"} (string, no type coercion)
    - key: -> {"key": None}
    - - item lines after a key -> {"key": ["item1", "item2"]}
    """
    result: Dict[str, Union[str, List[str], None]] = {}
    current_key: Optional[str] = None

    for line in yaml_text.split("\n"):
        stripped = line.strip()

        # Skip blank lines and comments
        if not stripped or stripped.startswith("#"):
            continue

        # List item: "- value" or "  - value"
        if stripped.startswith("- "):
            if current_key is not None:
                item_value = stripped[2:].strip()
                if current_key not in result or result[current_key] is None:
                    result[current_key] = []
                existing = result[current_key]
                if isinstance(existing, list):
                    existing.append(item_value)
            continue

        # Key-value pair: "key: value" or "key:"
        colon_idx = stripped.find(":")
        if colon_idx == -1:
            continue

        key = stripped[:colon_idx].strip()
        raw_value = stripped[colon_idx + 1:]

        if raw_value.strip():
            result[key] = raw_value.strip()
            current_key = None
        else:
            result[key] = None
            current_key = key

    return result
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_frontmatter.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add wos/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: add custom frontmatter parser (stdlib-only)"
```

---

### ~~Task 2: Migrate document.py from yaml to custom parser~~ [DONE]

**Files:**
- Modify: `wos/document.py`
- Modify: `tests/test_document.py`

**Step 1: Update tests for Document.extra removal**

In `tests/test_document.py`, make these changes:

1. In `TestDocument.test_minimal_fields` — remove `assert doc.extra == {}`
2. In `TestDocument.test_all_fields` — remove the `extra=` kwarg and the `doc.extra` assertions
3. In `TestParseDocument.test_minimal_frontmatter` — remove `assert doc.extra == {}`
4. In `TestParseDocument.test_extra_fields_preserved` — **rename to `test_unknown_fields_ignored`**, change assertions: verify that `doc.name`, `doc.description` are set, and that `doc` does NOT have attributes `status`, `priority` (unknown fields are simply not stored)
5. In `TestParseDocument.test_raises_valueerror_on_invalid_yaml` — update match string to work with new parser error messages

Updated `test_extra_fields_preserved` → `test_unknown_fields_ignored`:

```python
    def test_unknown_fields_ignored(self) -> None:
        from wos.document import parse_document

        text = (
            "---\n"
            "name: Custom Doc\n"
            "description: A document with extra fields\n"
            "status: draft\n"
            "priority: high\n"
            "tags:\n"
            "  - python\n"
            "  - testing\n"
            "---\n"
            "# Custom Doc\n"
        )
        doc = parse_document("context/misc/custom.md", text)
        assert doc.name == "Custom Doc"
        assert doc.description == "A document with extra fields"
        # Unknown fields are not stored — no extra dict
        assert not hasattr(doc, "status")
        assert not hasattr(doc, "priority")
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_document.py -v`
Expected: Some tests fail (the ones we changed assertions on)

**Step 3: Update document.py**

Replace `import yaml` with `from wos.frontmatter import parse_frontmatter`. Remove `extra` field from `Document`. Rewrite `parse_document()` to use the custom parser.

```python
"""Document dataclass and frontmatter parser.

Provides a single Document dataclass representing any WOS document
(topic, overview, research, plan) and a parse_document() function
that extracts YAML frontmatter into structured fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from wos.frontmatter import parse_frontmatter

# Known frontmatter fields extracted into Document attributes.
_KNOWN_FIELDS = {"name", "description", "type", "sources", "related"}


@dataclass
class Document:
    """A parsed WOS document with frontmatter metadata and body content."""

    path: str
    name: str
    description: str
    content: str
    type: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)


def parse_document(path: str, text: str) -> Document:
    """Parse a markdown document with YAML frontmatter.

    Extracts frontmatter between ``---`` delimiters. Known fields
    (name, description, type, sources, related) become Document
    attributes; unknown fields are ignored.

    Args:
        path: File path for the document.
        text: Raw markdown text including frontmatter.

    Returns:
        A Document instance with parsed metadata and body content.

    Raises:
        ValueError: If frontmatter is missing, or required fields
            (name, description) are absent.
    """
    try:
        fm, content = parse_frontmatter(text)
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc

    # ── Validate required fields ───────────────────────────────
    if "name" not in fm:
        raise ValueError(f"{path}: frontmatter missing required field 'name'")
    if "description" not in fm:
        raise ValueError(
            f"{path}: frontmatter missing required field 'description'"
        )

    # ── Extract known fields ───────────────────────────────────
    name: str = str(fm["name"]) if fm["name"] is not None else ""
    description: str = str(fm["description"]) if fm["description"] is not None else ""
    doc_type: Optional[str] = fm.get("type")
    if isinstance(doc_type, str):
        doc_type = doc_type
    else:
        doc_type = str(doc_type) if doc_type is not None else None
    sources: List[str] = fm.get("sources") or []
    related: List[str] = fm.get("related") or []

    return Document(
        path=path,
        name=name,
        description=description,
        content=content,
        type=doc_type,
        sources=sources,
        related=related,
    )
```

**Step 4: Run all tests**

Run: `python3 -m pytest tests/test_document.py tests/test_frontmatter.py -v`
Expected: All PASS

**Step 5: Run full test suite to catch regressions**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS (some tests may need adjustments if they reference `doc.extra`)

**Step 6: Commit**

```bash
git add wos/document.py tests/test_document.py
git commit -m "refactor: migrate document.py from pyyaml to custom parser, drop Document.extra"
```

---

### ~~Task 3: Replace requests with urllib in url_checker.py~~ [DONE]

**Files:**
- Modify: `wos/url_checker.py`
- Modify: `tests/test_url_checker.py`

**Step 1: Rewrite tests to mock urllib instead of requests**

Replace the entire `tests/test_url_checker.py`:

```python
"""Tests for wos.url_checker — HTTP HEAD/GET URL reachability checks.

All HTTP calls are mocked. No network traffic in tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from wos.url_checker import UrlCheckResult, check_url, check_urls

# ── UrlCheckResult dataclass ─────────────────────────────────────


def test_url_check_result_reachable() -> None:
    """UrlCheckResult stores reachable=True with status and no reason."""
    result = UrlCheckResult(url="https://example.com", status=200, reachable=True)
    assert result.url == "https://example.com"
    assert result.status == 200
    assert result.reachable is True
    assert result.reason is None


def test_url_check_result_unreachable_with_reason() -> None:
    """UrlCheckResult stores reachable=False with reason string."""
    result = UrlCheckResult(
        url="https://example.com/missing",
        status=404,
        reachable=False,
        reason="HTTP 404: not found",
    )
    assert result.url == "https://example.com/missing"
    assert result.status == 404
    assert result.reachable is False
    assert result.reason == "HTTP 404: not found"


# ── check_url ────────────────────────────────────────────────────


def _mock_response(status: int = 200) -> MagicMock:
    """Create a mock urllib response with the given status."""
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


@patch("wos.url_checker.urlopen")
def test_check_url_200_reachable(mock_urlopen: MagicMock) -> None:
    """HTTP 200 response marks URL as reachable."""
    mock_urlopen.return_value = _mock_response(200)
    result = check_url("https://example.com/page")
    assert result.reachable is True
    assert result.status == 200
    assert result.reason is None
    mock_urlopen.assert_called_once()


@patch("wos.url_checker.urlopen")
def test_check_url_404_unreachable(mock_urlopen: MagicMock) -> None:
    """HTTP 404 response marks URL as unreachable."""
    mock_urlopen.side_effect = HTTPError(
        "https://example.com/missing", 404, "Not Found", {}, None
    )
    result = check_url("https://example.com/missing")
    assert result.reachable is False
    assert result.status == 404
    assert result.reason is not None


@patch("wos.url_checker.urlopen")
def test_check_url_head_405_falls_back_to_get(mock_urlopen: MagicMock) -> None:
    """HEAD returning 405 triggers a GET fallback."""
    # First call (HEAD) raises 405, second call (GET) succeeds
    mock_urlopen.side_effect = [
        HTTPError("https://example.com/no-head", 405, "Method Not Allowed", {}, None),
        _mock_response(200),
    ]
    result = check_url("https://example.com/no-head")
    assert result.reachable is True
    assert result.status == 200
    assert mock_urlopen.call_count == 2


@patch("wos.url_checker.urlopen")
def test_check_url_connection_error(mock_urlopen: MagicMock) -> None:
    """Connection error returns status=0, reachable=False."""
    mock_urlopen.side_effect = URLError("DNS resolution failed")
    result = check_url("https://nonexistent.example.com")
    assert result.reachable is False
    assert result.status == 0
    assert result.reason is not None
    assert "DNS resolution failed" in result.reason


@patch("wos.url_checker.urlopen")
def test_check_url_timeout(mock_urlopen: MagicMock) -> None:
    """Timeout returns status=0, reachable=False."""
    mock_urlopen.side_effect = URLError("timed out")
    result = check_url("https://slow.example.com")
    assert result.reachable is False
    assert result.status == 0
    assert result.reason is not None


def test_check_url_invalid_scheme() -> None:
    """Non-HTTP/HTTPS URLs return reachable=False immediately."""
    result = check_url("ftp://files.example.com/data.csv")
    assert result.reachable is False
    assert result.status == 0
    assert result.reason is not None
    assert "http" in result.reason.lower() or "https" in result.reason.lower()


# ── check_urls (batch) ───────────────────────────────────────────


@patch("wos.url_checker.urlopen")
def test_check_urls_batch(mock_urlopen: MagicMock) -> None:
    """Batch check returns a result for each unique URL."""
    def side_effect(req, **kwargs):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        if "good" in url:
            return _mock_response(200)
        raise HTTPError(url, 404, "Not Found", {}, None)

    mock_urlopen.side_effect = side_effect

    results = check_urls([
        "https://example.com/good",
        "https://example.com/missing",
    ])
    assert len(results) == 2
    assert results[0].reachable is True
    assert results[1].reachable is False


def test_check_urls_empty_list() -> None:
    """Empty input returns empty output without any HTTP calls."""
    results = check_urls([])
    assert results == []


@patch("wos.url_checker.urlopen")
def test_check_urls_deduplicates(mock_urlopen: MagicMock) -> None:
    """Duplicate URLs are checked only once."""
    mock_urlopen.return_value = _mock_response(200)
    results = check_urls([
        "https://example.com/page",
        "https://example.com/page",
        "https://example.com/page",
    ])
    assert len(results) == 1
    assert results[0].url == "https://example.com/page"
    mock_urlopen.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_url_checker.py -v`
Expected: FAIL — importing `requests` will still work, but mocks target wrong things

**Step 3: Rewrite url_checker.py with urllib**

```python
"""URL reachability checker — HTTP HEAD with GET fallback.

Lightweight module for checking whether URLs are reachable.
Uses HEAD requests with a GET fallback when HEAD returns 405.
Used by validators to verify source URL reachability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


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
    - If HEAD returns 405, falls back to GET.
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
        req = Request(url, method="HEAD", headers=_HEADERS)
        resp = urlopen(req, timeout=_TIMEOUT)
        status = resp.status
    except HTTPError as exc:
        if exc.code == 405:
            # HEAD not allowed — fall back to GET
            return _try_get(url)
        return UrlCheckResult(
            url=url,
            status=exc.code,
            reachable=False,
            reason=f"HTTP {exc.code}",
        )
    except URLError as exc:
        return UrlCheckResult(
            url=url, status=0, reachable=False, reason=str(exc.reason)
        )
    except Exception as exc:
        return UrlCheckResult(
            url=url, status=0, reachable=False, reason=str(exc)
        )

    # 2xx and 3xx are reachable (urllib follows redirects, so we mostly see 2xx)
    if 200 <= status < 400:
        return UrlCheckResult(url=url, status=status, reachable=True)

    return UrlCheckResult(
        url=url,
        status=status,
        reachable=False,
        reason=f"HTTP {status}",
    )


def _try_get(url: str) -> UrlCheckResult:
    """Fallback GET request when HEAD returns 405."""
    try:
        req = Request(url, headers=_HEADERS)
        resp = urlopen(req, timeout=_TIMEOUT)
        status = resp.status
    except HTTPError as exc:
        return UrlCheckResult(
            url=url,
            status=exc.code,
            reachable=False,
            reason=f"HTTP {exc.code}",
        )
    except (URLError, Exception) as exc:
        reason = str(exc.reason) if hasattr(exc, "reason") else str(exc)
        return UrlCheckResult(
            url=url, status=0, reachable=False, reason=reason
        )

    if 200 <= status < 400:
        return UrlCheckResult(url=url, status=status, reachable=True)

    return UrlCheckResult(
        url=url, status=status, reachable=False, reason=f"HTTP {status}",
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
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_url_checker.py -v`
Expected: All PASS

**Step 5: Run full suite**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add wos/url_checker.py tests/test_url_checker.py
git commit -m "refactor: replace requests with urllib.request in url_checker"
```

---

### ~~Task 4: Remove dependencies and simplify research_protocol~~ [DONE]

**Files:**
- Modify: `pyproject.toml`
- Modify: `wos/research_protocol.py`
- Modify: `tests/test_research_protocol.py`

**Step 1: Remove CLI tests from test_research_protocol.py**

Delete the `TestCli` class and remove `main` from the import line. The import line becomes:

```python
from wos.research_protocol import (
    SearchEntry,
    SearchProtocol,
    format_protocol,
    format_protocol_summary,
)
```

**Step 2: Remove CLI code from research_protocol.py**

Remove `import argparse`, `import json`, `import sys` (no longer needed). Remove `main()` function and `if __name__ == "__main__":` block. Keep: dataclasses, formatters, `_protocol_from_json()`. The `import json` stays only if `_protocol_from_json` needs it — it doesn't (it takes a dict, not a string). Remove all three unused imports.

Updated imports:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
```

**Step 3: Remove runtime dependencies from pyproject.toml**

Change dependencies line:

```toml
dependencies = []
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_research_protocol.py -v`
Expected: All PASS (CLI tests removed, library tests unchanged)

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add pyproject.toml wos/research_protocol.py tests/test_research_protocol.py
git commit -m "refactor: remove runtime dependencies, strip research_protocol CLI"
```

---

## Phase 2: Validator & Output Refactoring

### ~~Task 5: Merge frontmatter checks and add warn/fail severity~~ [DONE]

**Files:**
- Modify: `wos/validators.py`
- Modify: `tests/test_validators.py`

**Step 1: Write new tests for merged check_frontmatter**

Add new test cases to `tests/test_validators.py`. The `TestCheckResearchSources` class is removed — its logic moves into `TestCheckFrontmatter`. Add tests for new warn-level checks:

```python
# Add to TestCheckFrontmatter:

    def test_research_without_sources_fail(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(type="research", sources=[])
        issues = check_frontmatter(doc)
        assert any(
            i["severity"] == "fail" and "sources" in i["issue"].lower()
            for i in issues
        )

    def test_research_with_sources_no_source_issue(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(
            type="research",
            sources=["https://example.com/source"],
        )
        issues = check_frontmatter(doc)
        assert not any("sources" in i["issue"].lower() for i in issues)

    def test_non_research_without_sources_ok(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(type="topic", sources=[])
        issues = check_frontmatter(doc)
        assert not any("sources" in i["issue"].lower() for i in issues)

    def test_dict_source_warns(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(sources=[
            {"url": "https://example.com", "title": "A"},
        ])
        issues = check_frontmatter(doc)
        assert any(i["severity"] == "warn" for i in issues)
        assert any("dict" in i["issue"].lower() for i in issues)

    def test_context_file_without_related_warns(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(
            path="context/api/auth.md",
            related=[],
        )
        issues = check_frontmatter(doc)
        assert any(
            i["severity"] == "warn" and "related" in i["issue"].lower()
            for i in issues
        )

    def test_artifact_file_without_related_no_warn(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(
            path="docs/research/topic.md",
            related=[],
        )
        issues = check_frontmatter(doc)
        assert not any("related" in i["issue"].lower() for i in issues)
```

**Step 2: Run tests to see failures**

Run: `python3 -m pytest tests/test_validators.py::TestCheckFrontmatter -v`
Expected: New tests fail (check_frontmatter doesn't have these checks yet)

**Step 3: Implement merged check_frontmatter**

In `wos/validators.py`, replace `check_frontmatter()` and `check_research_sources()` with a single merged function:

```python
def check_frontmatter(doc: Document, context_path: str = "context") -> List[dict]:
    """Check frontmatter fields: required fields, research sources, type issues.

    Args:
        doc: A parsed Document instance.
        context_path: Path prefix for context files (for related-field check).

    Returns:
        List of issue dicts with severity 'fail' or 'warn'.
    """
    issues: List[dict] = []

    # FAIL: required fields
    if not doc.name or not doc.name.strip():
        issues.append({
            "file": doc.path,
            "issue": "Frontmatter 'name' is empty",
            "severity": "fail",
        })
    if not doc.description or not doc.description.strip():
        issues.append({
            "file": doc.path,
            "issue": "Frontmatter 'description' is empty",
            "severity": "fail",
        })

    # FAIL: research documents must have sources
    if doc.type == "research" and not doc.sources:
        issues.append({
            "file": doc.path,
            "issue": "Research document has no sources",
            "severity": "fail",
        })

    # WARN: source items should be strings, not dicts
    for idx, source in enumerate(doc.sources):
        if isinstance(source, dict):
            issues.append({
                "file": doc.path,
                "issue": f"sources[{idx}] is a dict, expected a URL string",
                "severity": "warn",
            })

    # WARN: context files should have related fields
    if doc.path.startswith(context_path + "/") and not doc.related:
        issues.append({
            "file": doc.path,
            "issue": "Context file has no related fields",
            "severity": "warn",
        })

    return issues
```

Remove the standalone `check_research_sources()` function.

Update `validate_file()` to remove the `check_research_sources(doc)` call — it's now part of `check_frontmatter()`.

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_validators.py -v`
Expected: All PASS. Old `TestCheckResearchSources` tests should be updated or removed since the function is gone.

**Step 5: Commit**

```bash
git add wos/validators.py tests/test_validators.py
git commit -m "refactor: merge frontmatter checks, add warn/fail severity"
```

---

### ~~Task 6: Add check_content() for word count warnings~~ [DONE]

**Files:**
- Modify: `wos/validators.py`
- Modify: `tests/test_validators.py`

**Step 1: Write failing tests**

```python
class TestCheckContent:
    def test_short_context_file_no_warning(self) -> None:
        from wos.validators import check_content

        doc = _make_doc(
            path="context/api/auth.md",
            content="Word " * 200,
        )
        issues = check_content(doc)
        assert issues == []

    def test_long_context_file_warns(self) -> None:
        from wos.validators import check_content

        doc = _make_doc(
            path="context/api/auth.md",
            content="Word " * 900,
        )
        issues = check_content(doc)
        assert len(issues) == 1
        assert issues[0]["severity"] == "warn"
        assert "900" in issues[0]["issue"]

    def test_artifact_file_no_warning(self) -> None:
        from wos.validators import check_content

        doc = _make_doc(
            path="docs/research/topic.md",
            content="Word " * 2000,
        )
        issues = check_content(doc)
        assert issues == []

    def test_index_file_excluded(self) -> None:
        from wos.validators import check_content

        doc = _make_doc(
            path="context/api/_index.md",
            content="Word " * 2000,
        )
        issues = check_content(doc)
        assert issues == []

    def test_custom_max_words(self) -> None:
        from wos.validators import check_content

        doc = _make_doc(
            path="context/api/auth.md",
            content="Word " * 500,
        )
        issues = check_content(doc, max_words=400)
        assert len(issues) == 1

    def test_exactly_at_threshold_no_warning(self) -> None:
        from wos.validators import check_content

        doc = _make_doc(
            path="context/api/auth.md",
            content="Word " * 800,
        )
        issues = check_content(doc)
        assert issues == []
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validators.py::TestCheckContent -v`
Expected: FAIL — `check_content` not defined

**Step 3: Implement check_content**

```python
def check_content(
    doc: Document,
    context_path: str = "context",
    max_words: int = 800,
) -> List[dict]:
    """Warn when context files exceed word count threshold.

    Only checks files under context_path. Artifacts and _index.md
    files are excluded.

    Args:
        doc: A parsed Document instance.
        context_path: Path prefix for context files.
        max_words: Word count threshold (default 800).

    Returns:
        List of issue dicts. Empty if within threshold.
    """
    if not doc.path.startswith(context_path + "/"):
        return []
    if doc.path.endswith("_index.md"):
        return []

    word_count = len(doc.content.split())
    if word_count > max_words:
        return [{
            "file": doc.path,
            "issue": f"Context file is {word_count} words (threshold: {max_words})",
            "severity": "warn",
        }]
    return []
```

Add `check_content(doc)` call in `validate_file()` after the other checks.

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_validators.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add wos/validators.py tests/test_validators.py
git commit -m "feat: add check_content() for word count warnings on context files"
```

---

### ~~Task 7: Preamble-preserving index generation~~ [DONE]

**Files:**
- Modify: `wos/index.py`
- Modify: `tests/test_index.py`

**Step 1: Write failing tests**

```python
class TestPreamble:
    def test_extract_preamble_returns_text_between_heading_and_table(
        self, tmp_path: Path
    ) -> None:
        from wos.index import _extract_preamble

        index = tmp_path / "_index.md"
        index.write_text(
            "# My Area\n\nThis area covers authentication.\n\n"
            "| File | Description |\n| --- | --- |\n| [a.md](a.md) | Doc A |\n"
        )
        assert _extract_preamble(index) == "This area covers authentication."

    def test_extract_preamble_returns_none_when_no_preamble(
        self, tmp_path: Path
    ) -> None:
        from wos.index import _extract_preamble

        index = tmp_path / "_index.md"
        index.write_text(
            "# My Area\n\n| File | Description |\n| --- | --- |\n"
        )
        assert _extract_preamble(index) is None

    def test_extract_preamble_returns_none_for_missing_file(
        self, tmp_path: Path
    ) -> None:
        from wos.index import _extract_preamble

        assert _extract_preamble(tmp_path / "nonexistent.md") is None

    def test_generate_index_includes_preamble(self, tmp_path: Path) -> None:
        from wos.index import generate_index

        (tmp_path / "doc.md").write_text(
            "---\nname: Doc\ndescription: A document\n---\n# Doc\n"
        )
        result = generate_index(tmp_path, preamble="This area covers testing.")
        lines = result.splitlines()
        # Preamble should be between heading and table
        assert lines[0].startswith("# ")
        assert "This area covers testing." in result
        heading_idx = 0
        table_idx = next(
            i for i, l in enumerate(lines) if l.startswith("| File")
        )
        preamble_idx = next(
            i for i, l in enumerate(lines)
            if "This area covers testing." in l
        )
        assert heading_idx < preamble_idx < table_idx

    def test_generate_index_without_preamble_unchanged(
        self, tmp_path: Path
    ) -> None:
        from wos.index import generate_index

        (tmp_path / "doc.md").write_text(
            "---\nname: Doc\ndescription: A doc\n---\n"
        )
        result = generate_index(tmp_path)
        lines = result.splitlines()
        # No blank line with text between heading and table
        assert lines[0].startswith("# ")
        # Next non-empty line should be table header
        non_empty = [l for l in lines[1:] if l.strip()]
        assert non_empty[0].startswith("| File")

    def test_preamble_preserved_during_regeneration(
        self, tmp_path: Path
    ) -> None:
        from wos.index import generate_index, _extract_preamble

        (tmp_path / "doc.md").write_text(
            "---\nname: Doc\ndescription: A document\n---\n# Doc\n"
        )
        # Write initial index with preamble
        initial = generate_index(tmp_path, preamble="My area description.")
        (tmp_path / "_index.md").write_text(initial)

        # Extract preamble and regenerate
        preamble = _extract_preamble(tmp_path / "_index.md")
        regenerated = generate_index(tmp_path, preamble=preamble)

        assert "My area description." in regenerated
        assert initial == regenerated
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_index.py::TestPreamble -v`
Expected: FAIL

**Step 3: Implement preamble support**

Add `_extract_preamble()` and update `generate_index()` in `wos/index.py`:

```python
def _extract_preamble(index_path: Path) -> Optional[str]:
    """Extract preamble text from an existing _index.md.

    The preamble is any text between the heading line and the first
    table line (starting with '|'). Returns None if no preamble
    exists or the file is missing.
    """
    if not index_path.is_file():
        return None

    try:
        content = index_path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = content.splitlines()
    heading_idx = None
    table_idx = None

    for i, line in enumerate(lines):
        if heading_idx is None and line.startswith("# "):
            heading_idx = i
        elif heading_idx is not None and line.startswith("|"):
            table_idx = i
            break

    if heading_idx is None or table_idx is None:
        return None

    # Extract lines between heading and table, strip blanks
    preamble_lines = [
        l for l in lines[heading_idx + 1:table_idx] if l.strip()
    ]
    if not preamble_lines:
        return None

    return "\n".join(preamble_lines)
```

Update `generate_index()` signature and body:

```python
def generate_index(directory: Path, preamble: Optional[str] = None) -> str:
```

After the heading line (`lines = [f"# {heading}\n"]`), insert:

```python
    if preamble:
        lines.append("")
        lines.append(preamble)
```

Update `check_index_sync()` to extract and pass preamble when regenerating for comparison:

```python
def check_index_sync(directory: Path) -> List[dict]:
    index_path = directory / "_index.md"

    if not index_path.is_file():
        return [{
            "file": str(index_path),
            "issue": "_index.md is missing",
            "severity": "fail",
        }]

    # Preserve preamble when comparing
    preamble = _extract_preamble(index_path)
    current_content = generate_index(directory, preamble=preamble)
    existing_content = index_path.read_text(encoding="utf-8")

    if current_content != existing_content:
        return [{
            "file": str(index_path),
            "issue": "_index.md is out of sync with directory contents",
            "severity": "fail",
        }]

    return []
```

Also update `scripts/reindex.py` to preserve preambles when regenerating:

In `_reindex_directory()`:

```python
def _reindex_directory(directory, generate_index_fn, extract_preamble_fn) -> bool:
    # ... existing has_md_files / has_subdirs checks ...
    index_path = directory / "_index.md"
    preamble = extract_preamble_fn(index_path)
    content = generate_index_fn(directory, preamble=preamble)
    index_path.write_text(content, encoding="utf-8")
    return True
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_index.py -v`
Expected: All PASS

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add wos/index.py tests/test_index.py scripts/reindex.py
git commit -m "feat: preamble-preserving index generation"
```

---

### ~~Task 8: Add preamble warning check to validators~~ [DONE]

**Files:**
- Modify: `wos/validators.py`
- Modify: `tests/test_validators.py`

**Step 1: Write failing tests**

```python
class TestCheckPreamble:
    def test_index_with_preamble_no_warning(self, tmp_path: Path) -> None:
        from wos.index import generate_index
        from wos.validators import check_all_indexes

        area = tmp_path / "context" / "api"
        area.mkdir(parents=True)
        (area / "auth.md").write_text(
            "---\nname: Auth\ndescription: Auth docs\n---\n"
        )
        index = generate_index(area, preamble="This area covers the API.")
        (area / "_index.md").write_text(index)
        (tmp_path / "context" / "_index.md").write_text(
            generate_index(tmp_path / "context", preamble="All context.")
        )

        issues = check_all_indexes(tmp_path / "context")
        warn_issues = [i for i in issues if i["severity"] == "warn"]
        assert not any("preamble" in i["issue"].lower() for i in warn_issues)

    def test_index_without_preamble_warns(self, tmp_path: Path) -> None:
        from wos.index import generate_index
        from wos.validators import check_all_indexes

        area = tmp_path / "context" / "api"
        area.mkdir(parents=True)
        (area / "auth.md").write_text(
            "---\nname: Auth\ndescription: Auth docs\n---\n"
        )
        # No preamble
        index = generate_index(area)
        (area / "_index.md").write_text(index)
        (tmp_path / "context" / "_index.md").write_text(
            generate_index(tmp_path / "context")
        )

        issues = check_all_indexes(tmp_path / "context")
        warn_issues = [i for i in issues if i["severity"] == "warn"]
        assert any("area description" in i["issue"].lower() for i in warn_issues)
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validators.py::TestCheckPreamble -v`
Expected: FAIL

**Step 3: Add preamble check to check_all_indexes**

In `check_all_indexes()`, after the sync check, add a preamble check:

```python
from wos.index import check_index_sync, _extract_preamble

def check_all_indexes(directory: Path) -> List[dict]:
    issues: List[dict] = []
    if not directory.is_dir():
        return issues

    issues.extend(check_index_sync(directory))

    # WARN: index exists but has no preamble (area description)
    index_path = directory / "_index.md"
    if index_path.is_file() and _extract_preamble(index_path) is None:
        issues.append({
            "file": str(index_path),
            "issue": "Index has no area description (preamble)",
            "severity": "warn",
        })

    for entry in sorted(directory.iterdir()):
        if entry.is_dir():
            issues.extend(check_all_indexes(entry))

    return issues
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_validators.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add wos/validators.py tests/test_validators.py
git commit -m "feat: warn when _index.md lacks area description preamble"
```

---

### ~~Task 9: LLM-friendly output format and merge validate.py into audit.py~~ [DONE]

**Files:**
- Modify: `scripts/audit.py`
- Modify: `scripts/reindex.py`
- Delete: `scripts/validate.py`
- Modify: `tests/test_audit.py`

**Step 1: Rewrite test_audit.py for new output format**

Replace the entire test file to match the new output format (summary + table, warn/fail, `--strict`, single-file mode):

```python
"""Tests for scripts/audit.py — LLM-friendly CLI output."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch


def _run_audit(*args: str, issues: list[dict] | None = None) -> tuple[str, str, int]:
    """Run audit.main() with the given CLI args, returning (stdout, stderr, exitcode)."""
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    exit_code = 0

    mock_target = "wos.validators.validate_project"

    with patch.object(sys, "argv", ["audit.py", *args]):
        with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
            try:
                if issues is not None:
                    with patch(mock_target, return_value=issues):
                        from scripts.audit import main
                        main()
                else:
                    from scripts.audit import main
                    main()
            except SystemExit as exc:
                exit_code = exc.code if exc.code is not None else 0

    return captured_stdout.getvalue(), captured_stderr.getvalue(), exit_code


class TestSummaryLine:
    def test_summary_shows_fail_and_warn_counts(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        issues = [
            {"file": str(root / "a.md"), "issue": "Problem A", "severity": "fail"},
            {"file": str(root / "b.md"), "issue": "Problem B", "severity": "warn"},
        ]
        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)
        assert "1 fail" in stdout
        assert "1 warn" in stdout

    def test_no_issues_shows_all_passed(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=[])
        assert "All checks passed." in stdout


class TestTableFormat:
    def test_output_uses_relative_paths(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        issues = [
            {
                "file": str(root / "context" / "api" / "auth.md"),
                "issue": "Frontmatter 'name' is empty",
                "severity": "fail",
            },
        ]
        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)
        assert str(root) not in stdout
        assert "context/api/auth.md" in stdout

    def test_table_has_severity_column(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        issues = [
            {"file": str(root / "a.md"), "issue": "Problem", "severity": "fail"},
            {"file": str(root / "b.md"), "issue": "Drift", "severity": "warn"},
        ]
        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)
        assert "fail" in stdout
        assert "warn" in stdout


class TestExitCodes:
    def test_exit_1_on_fail_issues(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        issues = [
            {"file": str(root / "a.md"), "issue": "Problem", "severity": "fail"},
        ]
        _, _, code = _run_audit("--root", str(root), "--no-urls", issues=issues)
        assert code == 1

    def test_exit_0_on_warn_only(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        issues = [
            {"file": str(root / "a.md"), "issue": "Drift", "severity": "warn"},
        ]
        _, _, code = _run_audit("--root", str(root), "--no-urls", issues=issues)
        assert code == 0

    def test_exit_1_on_warn_with_strict(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        issues = [
            {"file": str(root / "a.md"), "issue": "Drift", "severity": "warn"},
        ]
        _, _, code = _run_audit(
            "--root", str(root), "--no-urls", "--strict", issues=issues,
        )
        assert code == 1

    def test_exit_0_on_no_issues(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        _, _, code = _run_audit("--root", str(root), "--no-urls", issues=[])
        assert code == 0


class TestJsonOutput:
    def test_json_output_unchanged(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        issues = [
            {"file": str(root / "a.md"), "issue": "Problem", "severity": "fail"},
        ]
        stdout, _, _ = _run_audit(
            "--root", str(root), "--no-urls", "--json", issues=issues,
        )
        parsed = json.loads(stdout)
        assert isinstance(parsed, list)
        assert len(parsed) == 1


class TestSingleFileMode:
    def test_single_file_validation(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()
        md_file = root / "context" / "test.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text(
            "---\nname: Test\ndescription: A test\n---\n# Test\n"
        )
        # Single file mode — mock validate_file instead
        with patch("wos.validators.validate_file", return_value=[]) as mock_vf:
            stdout, _, code = _run_audit(
                "--root", str(root), "--no-urls", str(md_file),
            )
        mock_vf.assert_called_once()
        assert code == 0


class TestFixOutput:
    def test_fix_messages_use_relative_paths(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        idx_dir = root / "artifacts" / "plans"
        idx_dir.mkdir(parents=True)
        idx_file = idx_dir / "_index.md"
        idx_file.write_text("")
        issues = [
            {
                "file": str(idx_file),
                "issue": "_index.md is out of sync with directory contents",
                "severity": "fail",
            },
        ]
        with patch("wos.validators.validate_project", return_value=issues):
            _, stderr, _ = _run_audit("--root", str(root), "--no-urls", "--fix")
        assert str(root) not in stderr
        assert "docs/plans/_index.md" in stderr
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_audit.py -v`
Expected: Multiple failures (new format, new args)

**Step 3: Rewrite audit.py**

```python
#!/usr/bin/env python3
"""Run WOS validation checks on a project.

Usage:
    python3 scripts/audit.py [FILE] [--root DIR] [--no-urls] [--json] [--fix] [--strict] [--context-max-words N]
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def _relative_path(file_path: str, root: Path) -> str:
    """Return file_path relative to root, falling back to the original."""
    try:
        return str(Path(file_path).relative_to(root))
    except ValueError:
        return file_path


def main() -> None:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser(
        description="Run WOS validation checks on a project.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Optional: validate a single file instead of the whole project",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--no-urls",
        action="store_true",
        help="Skip URL reachability checks",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output issues as JSON",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Regenerate out-of-sync or missing _index.md files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any issue (including warnings)",
    )
    parser.add_argument(
        "--context-max-words",
        type=int,
        default=800,
        help="Word count threshold for context file warnings (default: 800)",
    )
    args = parser.parse_args()

    # Deferred imports — keeps --help fast
    from wos.index import generate_index
    from wos.validators import validate_file, validate_project

    root = Path(args.root).resolve()

    # Single-file or project mode
    if args.file:
        file_path = Path(args.file).resolve()
        issues = validate_file(file_path, root, verify_urls=not args.no_urls)
    else:
        issues = validate_project(root, verify_urls=not args.no_urls)

    # --fix: regenerate _index.md files that are out of sync or missing
    if args.fix:
        fixed: list[str] = []
        remaining: list[dict] = []
        for issue in issues:
            file_path_str = issue["file"]
            msg = issue["issue"]
            if (
                file_path_str.endswith("_index.md")
                and ("out of sync" in msg or "missing" in msg)
            ):
                idx_path = Path(file_path_str)
                directory = idx_path.parent
                content = generate_index(directory)
                idx_path.write_text(content, encoding="utf-8")
                fixed.append(file_path_str)
                print(
                    f"Fixed: {_relative_path(file_path_str, root)}",
                    file=sys.stderr,
                )
            else:
                remaining.append(issue)
        issues = remaining

    # Count by severity
    fail_count = sum(1 for i in issues if i["severity"] == "fail")
    warn_count = sum(1 for i in issues if i["severity"] == "warn")

    # Output
    if args.json_output:
        print(json.dumps(issues, indent=2))
    elif issues:
        # Count unique files
        file_count = len({i["file"] for i in issues})
        print(f"{fail_count} fail, {warn_count} warn across {file_count} files")
        print()
        print(f"{'file':<40} | {'sev':<4} | issue")
        for issue in issues:
            rel = _relative_path(issue["file"], root)
            sev = issue["severity"]
            print(f"{rel:<40} | {sev:<4} | {issue['issue']}")
    else:
        print("All checks passed.")

    # Exit code: 1 if any fail, or if --strict and any issue
    has_failures = fail_count > 0
    has_any = len(issues) > 0
    sys.exit(1 if has_failures or (args.strict and has_any) else 0)


if __name__ == "__main__":
    main()
```

**Step 4: Update reindex.py output**

Change the `main()` function's final print in `scripts/reindex.py`:

```python
    print(f"wrote {count} index files")
```

(lowercase, concise)

**Step 5: Delete scripts/validate.py**

```bash
rm scripts/validate.py
```

**Step 6: Run tests**

Run: `python3 -m pytest tests/test_audit.py -v`
Expected: All PASS

Run: `python3 -m pytest tests/ -v`
Expected: All PASS (no test file references validate.py directly)

**Step 7: Commit**

```bash
git add scripts/audit.py scripts/reindex.py tests/test_audit.py
git rm scripts/validate.py
git commit -m "feat: LLM-friendly output, merge validate.py into audit.py, add --strict"
```

---

## Phase 3: Skill Layer

### ~~Task 10: Update /wos:create skill~~ [DONE]

**Files:**
- Modify: `skills/create/SKILL.md`

**Step 1: Update SKILL.md**

Add preamble prompt to area creation, word count advisory and related-field prompting to document creation:

In section "## 2. Add Area", after step 2 ("Create `context/{area}/`"):

Add: "3. Ask the user for a 1-2 sentence area description. Write it as the preamble in `_index.md` above the file table."

In section "## 3. Create Document", after step 4 (document content):

Add:
```
5. **Word count check** — Count words in the generated content. If the context file exceeds 800 words, note the count and suggest splitting into multiple focused files. This is advisory, not blocking.
6. **Related fields** — Scan existing files in the target area for potential `related:` candidates. Present suggestions to the user. If they confirm, add `related:` entries to the frontmatter. Ask whether referenced files should also link back (bidirectional linking).
```

Update step numbers for reindex (now step 7).

**Step 2: Commit**

```bash
git add skills/create/SKILL.md
git commit -m "feat: update /create skill with preamble, word count, and related-field prompts"
```

---

### ~~Task 11: Update /wos:audit skill~~ [DONE]

**Files:**
- Modify: `skills/audit/SKILL.md`

**Step 1: Update SKILL.md**

Update output format examples, severity descriptions, exit code semantics, and add `--strict` and `--context-max-words` flags. Update check descriptions to reflect merged frontmatter check and new content check.

Replace the check descriptions with:

```markdown
## The Checks

### 1. Frontmatter Validation (fail + warn)

Verifies:
- **fail:** `name` and `description` are non-empty
- **fail:** `type: research` documents have a non-empty `sources` list
- **warn:** Source items should be URL strings, not dicts
- **warn:** Context files should have `related` fields

### 2. Content Length (warn)

Warns when context files exceed 800 words (configurable via `--context-max-words`).
Artifacts and `_index.md` files are excluded.

### 3. Source URL Reachability (fail)

Checks that every URL in `sources` is reachable via HTTP.
Skipped with `--no-urls`.

### 4. Related Path Validation (fail)

Checks that local file paths in `related` exist on disk.

### 5. Index Sync (fail + warn)

- **fail:** `_index.md` missing or out of sync
- **warn:** `_index.md` has no area description (preamble)
```

Update the output format section:

```markdown
## Interpreting Results

Summary line first, then table:

```
2 fail, 1 warn across 15 files

file                              | sev  | issue
context/api/auth.md               | fail | Frontmatter 'name' is empty
context/api/_index.md             | warn | Index has no area description (preamble)
```

Exit code: 1 if any `fail`, 0 if only `warn`. Use `--strict` to exit 1 on any issue.
```

**Step 2: Commit**

```bash
git add skills/audit/SKILL.md
git commit -m "docs: update /audit skill for new output format and severity levels"
```

---

### ~~Task 12: Update /wos:research skill references~~ [DONE]

**Files:**
- Modify: `skills/research/references/python-utilities.md`
- Modify: `skills/research/references/research-workflow.md`
- Modify: `skills/research/SKILL.md`

**Step 1: Update python-utilities.md**

- Remove the "## Format Search Protocol" section (CLI is gone)
- Update "## Validate a Single Document" to use `audit.py FILE` instead of `validate.py`
- Update output format examples to match new table format

**Step 2: Update research-workflow.md**

Replace the `echo '<protocol_json>' | python3 -m wos.research_protocol format` instruction with:

"Format the search protocol as a markdown table directly in the document. Use this format:

```markdown
| Query | Source | Date Range | Found | Used |
|-------|--------|------------|-------|------|
| search terms | google | 2024-2026 | 12 | 3 |
```

Include a one-line summary near the top: `N searches across M sources, X results found, Y used`"

**Step 3: Update SKILL.md compatibility line**

Change: `"Requires Python 3, WOS plugin (url_checker, validate, reindex), WebSearch, WebFetch"`
To: `"Requires Python 3 (stdlib only), WOS plugin (audit, reindex), WebSearch, WebFetch"`

**Step 4: Commit**

```bash
git add skills/research/references/python-utilities.md skills/research/references/research-workflow.md skills/research/SKILL.md
git commit -m "docs: update research skill for stdlib migration, remove protocol CLI refs"
```

---

### ~~Task 13: Create /wos:distill skill~~ [DONE]

**Files:**
- Create: `skills/distill/SKILL.md`
- Create: `skills/distill/references/distillation-guidelines.md`

**Step 1: Create SKILL.md**

```markdown
---
name: distill
description: >
  This skill should be used when the user wants to "distill research",
  "extract findings", "create context from research", "summarize research
  into context files", "operationalize research", or convert any research
  artifact into focused context documents.
argument-hint: "[path to research artifact]"
user-invocable: true
---

# Distill

Convert research artifacts into focused context files.

## Workflow

### 1. Input

Accept a research artifact path from the user. If none provided, scan
`docs/research/` for the most recently modified `.md` file and confirm.

### 2. Analyze

Read the research document and identify discrete findings:
- Each finding should be a self-contained insight
- Note confidence level (HIGH, MODERATE, LOW) based on evidence strength
- Note evidence type (empirical, expert consensus, case study, theoretical)

### 3. Propose

Present a distillation plan as a table:

| # | Finding | Target Area | Filename | Words (est.) |
|---|---------|-------------|----------|--------------|
| 1 | Key finding one | context/area/ | finding-one.md | ~400 |

User approves, edits, or rejects individual rows.

### 4. Generate

For each approved finding:

1. Write a 200-800 word context file with frontmatter:
   ```yaml
   ---
   name: [Concise title]
   description: [One-sentence summary]
   type: reference
   sources:
     - [Carry forward relevant URLs from research]
   related:
     - [Path to source research artifact]
     - [Paths to sibling distilled files]
   ---
   ```

2. Follow the lost-in-the-middle convention:
   - **Top:** Key insight and actionable guidance
   - **Middle:** Detail, examples, context
   - **Bottom:** Takeaways or quick-reference

3. Report word count after writing. If >800 words, suggest splitting.

### 5. Integrate

1. Run `python3 scripts/reindex.py --root .`
2. Update the source research artifact's `related:` field to link
   forward to the new context files
3. Run `python3 scripts/audit.py --root . --no-urls` to verify

## Key Constraints

- **User controls granularity.** They pick which findings become standalone
  files vs. which get folded into existing files. Propose, don't decide.
- **Context files target 200-800 words.** This is advisory. If a finding
  needs more space, note it and proceed.
- **Carry forward sources.** Each context file should trace back to the
  original evidence via `sources:` URLs.
- **Bidirectional linking.** New files link to research via `related:`.
  Research links to new files via `related:`. Ask before modifying.
```

**Step 2: Create distillation-guidelines.md**

```markdown
# Distillation Guidelines

## What Makes a Good Context File

A context file distilled from research should be:

1. **Atomic** — one concept per file (Zettelkasten principle)
2. **Actionable** — reader knows what to do after reading
3. **Traceable** — sources link back to evidence
4. **Concise** — 200-800 words targets optimal RAG retrieval
5. **Structured** — key insight top, detail middle, takeaway bottom

## Splitting Heuristics

Split a finding into multiple files when:
- It covers more than one distinct concept
- Different aspects serve different audiences
- The finding has both a "what" and a "how" that are independently useful

Merge findings into a single file when:
- They're tightly coupled and don't make sense independently
- Combined they still fit under 800 words
- They serve the same audience with the same purpose

## Word Count Rationale

| Range | Use Case |
|-------|----------|
| <200 words | Too thin — probably needs more context or should be merged |
| 200-500 words | Ideal for focused reference files |
| 500-800 words | Good for explanatory context with examples |
| >800 words | Consider splitting — RAG retrieval degrades, attention loss risk |

## Confidence Mapping

When distilling, map research confidence levels to context file framing:

- **HIGH confidence** — state directly: "X works because Y"
- **MODERATE confidence** — qualify: "Evidence suggests X, based on Y"
- **LOW confidence** — flag: "Early evidence indicates X, but Z remains uncertain"
```

**Step 3: Commit**

```bash
git add skills/distill/SKILL.md skills/distill/references/distillation-guidelines.md
git commit -m "feat: add /wos:distill skill for research-to-context distillation"
```

---

### ~~Task 14: Version bump and CLAUDE.md updates~~ [DONE]

**Files:**
- Modify: `pyproject.toml` (version only — deps already cleared in Task 4)
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CLAUDE.md`

**Step 1: Bump version to 0.4.0**

In `pyproject.toml`, change `version = "0.3.6"` to `version = "0.4.0"`.
In `plugin.json`, change `"version": "0.3.6"` to `"version": "0.4.0"`.
In `marketplace.json`, change `"version": "0.3.6"` to `"version": "0.4.0"`.

**Step 2: Update CLAUDE.md**

Update the architecture section:

- Add `frontmatter.py` to module list: `frontmatter.py` — custom YAML subset parser (stdlib-only)
- Remove mention of `validate.py` script
- Update `document.py` description: remove "YAML frontmatter parser" (now in frontmatter.py)
- Update validation description: "5 validation checks" stays but update descriptions
- Add `/wos:distill` to skills table (now 7 skills)
- Update dependencies line: `No runtime dependencies (stdlib only)`
- Update check descriptions to mention warn/fail severity

**Step 3: Commit**

```bash
git add pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json CLAUDE.md
git commit -m "chore: bump version to 0.4.0, update CLAUDE.md for stdlib migration"
```

---

### ~~Task 15: Final verification~~ [DONE]

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 2: Run lint**

Run: `ruff check wos/ tests/ scripts/` (if ruff is available)
Expected: No errors

**Step 3: Verify no runtime dependency imports**

Run: `grep -r "import yaml\|import requests\|import pydantic\|from yaml\|from requests\|from pydantic" wos/ scripts/`
Expected: No matches

**Step 4: Verify tests don't import removed dependencies for non-mock purposes**

Run: `grep -r "import yaml\|import requests\|import pydantic" tests/`
Expected: No matches (old mocks of requests should be gone)

**Step 5: Run audit on the WOS repo itself**

Run: `python3 scripts/audit.py --root . --no-urls`
Expected: Output uses new format. No fail-severity issues.
