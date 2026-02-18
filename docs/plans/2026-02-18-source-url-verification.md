# Source URL Verification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `wos/source_verification.py` module that mechanically verifies source URLs resolve and cited titles match page content, integrated into the `/wos:research` skill workflow.

**Architecture:** A single Python module with `verify_sources()` as the core function, a `VerificationResult` dataclass for structured output, and a `__main__` block for CLI invocation via `python3 -m wos.source_verification`. The research skill workflow gets a new "Verify Sources" phase inserted between source gathering and SIFT evaluation.

**Tech Stack:** Python 3.9+, `requests` for HTTP, `html.parser` for title extraction, `dataclasses` + `json` for output. Tests use `unittest.mock.patch` to mock `requests.get`.

**Design doc:** `docs/plans/2026-02-18-source-url-verification-design.md`

**Issue:** [#6](https://github.com/bcbeidel/wos/issues/6)

---

### Task 1: Add `requests` dependency

**Files:**
- Modify: `pyproject.toml:10-13`

**Step 1: Add requests to dependencies**

In `pyproject.toml`, add `"requests>=2.28"` to the `dependencies` list:

```toml
dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "requests>=2.28",
]
```

**Step 2: Install updated dependencies**

Run: `pip install -e ".[dev]"`
Expected: Successfully installs requests

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add requests dependency for source URL verification"
```

---

### Task 2: Title normalization and matching

**Files:**
- Create: `wos/source_verification.py`
- Create: `tests/test_source_verification.py`

**Step 1: Write the failing tests for `normalize_title` and `titles_match`**

```python
"""Tests for wos.source_verification — source URL verification."""

from __future__ import annotations

from wos.source_verification import normalize_title, titles_match


# ── Title normalization ─────────────────────────────────────────


def test_normalize_lowercases():
    assert normalize_title("PEP 8 Style Guide") == "pep 8 style guide"


def test_normalize_strips_punctuation():
    assert normalize_title("Hello, World!") == "hello world"


def test_normalize_collapses_whitespace():
    assert normalize_title("  foo   bar  ") == "foo bar"


def test_normalize_strips_unicode_dashes():
    assert normalize_title("PEP 8 \u2013 Style Guide") == "pep 8 style guide"


# ── Title matching ──────────────────────────────────────────────


def test_titles_match_exact():
    assert titles_match("Python Tutorial", "Python Tutorial") is True


def test_titles_match_substring_cited_in_page():
    assert titles_match("Style Guide", "PEP 8 Style Guide for Python") is True


def test_titles_match_substring_page_in_cited():
    assert titles_match("PEP 8 Style Guide for Python Code", "PEP 8 Style Guide") is True


def test_titles_match_case_insensitive():
    assert titles_match("python tutorial", "Python Tutorial") is True


def test_titles_no_match():
    assert titles_match(
        "The Maximum Effective Context Window",
        "Context Is What You Need",
    ) is False
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_source_verification.py -v`
Expected: FAIL — `ImportError: cannot import name 'normalize_title'`

**Step 3: Write minimal implementation**

Create `wos/source_verification.py`:

```python
"""Source URL verification — checks that cited URLs resolve and titles match.

Provides verify_sources() for batch verification and a CLI entry point
via `python3 -m wos.source_verification`.
"""

from __future__ import annotations

import re


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = title.lower()
    # Replace unicode dashes with spaces
    text = text.replace("\u2013", " ").replace("\u2014", " ")
    # Strip punctuation (keep alphanumeric and spaces)
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def titles_match(cited: str, page: str) -> bool:
    """Check if normalized titles match via substring containment."""
    norm_cited = normalize_title(cited)
    norm_page = normalize_title(page)
    if not norm_cited or not norm_page:
        return False
    return norm_cited in norm_page or norm_page in norm_cited
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_source_verification.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add wos/source_verification.py tests/test_source_verification.py
git commit -m "feat: add title normalization and matching for source verification"
```

---

### Task 3: HTML title extraction

**Files:**
- Modify: `wos/source_verification.py`
- Modify: `tests/test_source_verification.py`

**Step 1: Write failing tests for `extract_page_title`**

Append to `tests/test_source_verification.py`:

```python
from wos.source_verification import extract_page_title


# ── Title extraction ────────────────────────────────────────────


def test_extract_title_tag():
    html = "<html><head><title>My Page</title></head><body></body></html>"
    assert extract_page_title(html) == "My Page"


def test_extract_title_tag_with_whitespace():
    html = "<title>  Spaced Title  </title>"
    assert extract_page_title(html) == "Spaced Title"


def test_extract_h1_fallback():
    html = "<html><body><h1>Heading Title</h1><p>content</p></body></html>"
    assert extract_page_title(html) == "Heading Title"


def test_extract_title_prefers_title_over_h1():
    html = "<html><head><title>Title Tag</title></head><body><h1>H1 Tag</h1></body></html>"
    assert extract_page_title(html) == "Title Tag"


def test_extract_no_title_returns_none():
    html = "<html><body><p>Just a paragraph</p></body></html>"
    assert extract_page_title(html) is None


def test_extract_empty_title_falls_back_to_h1():
    html = "<html><head><title></title></head><body><h1>Fallback</h1></body></html>"
    assert extract_page_title(html) == "Fallback"


def test_extract_empty_html():
    assert extract_page_title("") is None
```

**Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_source_verification.py::test_extract_title_tag -v`
Expected: FAIL — `ImportError: cannot import name 'extract_page_title'`

**Step 3: Write minimal implementation**

Add to `wos/source_verification.py`:

```python
from html.parser import HTMLParser
from typing import Optional


class _TitleParser(HTMLParser):
    """Extract <title> and first <h1> from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._in_h1 = False
        self.title: Optional[str] = None
        self.h1: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "title":
            self._in_title = True
        elif tag == "h1" and self.h1 is None:
            self._in_h1 = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title or "") + data
        elif self._in_h1:
            self.h1 = (self.h1 or "") + data


def extract_page_title(html: str) -> Optional[str]:
    """Extract page title from HTML. Tries <title>, falls back to <h1>."""
    parser = _TitleParser()
    try:
        parser.feed(html)
    except Exception:
        return None
    title = (parser.title or "").strip()
    if title:
        return title
    h1 = (parser.h1 or "").strip()
    return h1 if h1 else None
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_source_verification.py -v`
Expected: All 16 tests PASS

**Step 5: Commit**

```bash
git add wos/source_verification.py tests/test_source_verification.py
git commit -m "feat: add HTML title extraction for source verification"
```

---

### Task 4: VerificationResult and `verify_source` (single source)

**Files:**
- Modify: `wos/source_verification.py`
- Modify: `tests/test_source_verification.py`

**Step 1: Write failing tests for single-source verification**

Append to `tests/test_source_verification.py`:

```python
from unittest.mock import MagicMock, patch

import requests

from wos.source_verification import VerificationResult, verify_source


# ── Single source verification ──────────────────────────────────


def _mock_response(
    status_code: int = 200,
    text: str = "",
    url: str = "https://example.com",
) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    resp.url = url
    return resp


@patch("wos.source_verification.requests.get")
def test_200_title_match(mock_get):
    mock_get.return_value = _mock_response(
        text="<title>Python Tutorial</title>",
        url="https://docs.python.org/tutorial",
    )
    result = verify_source("https://docs.python.org/tutorial", "Python Tutorial")
    assert result.action == "ok"
    assert result.http_status == 200
    assert result.title_match is True


@patch("wos.source_verification.requests.get")
def test_200_title_mismatch(mock_get):
    mock_get.return_value = _mock_response(
        text="<title>Context Is What You Need</title>",
        url="https://arxiv.org/abs/2509.21361",
    )
    result = verify_source(
        "https://arxiv.org/abs/2509.21361",
        "The Maximum Effective Context Window",
    )
    assert result.action == "flagged"
    assert result.title_match is False
    assert "title mismatch" in result.reason.lower()


@patch("wos.source_verification.requests.get")
def test_200_no_title_tag(mock_get):
    mock_get.return_value = _mock_response(
        text="<html><body>No title here</body></html>",
        url="https://example.com",
    )
    result = verify_source("https://example.com", "Some Title")
    assert result.action == "ok"
    assert result.title_match is None
    assert result.page_title is None


@patch("wos.source_verification.requests.get")
def test_404(mock_get):
    mock_get.return_value = _mock_response(status_code=404)
    result = verify_source("https://example.com/gone", "Gone Page")
    assert result.action == "removed"
    assert result.http_status == 404


@patch("wos.source_verification.requests.get")
def test_403_paywall(mock_get):
    mock_get.return_value = _mock_response(status_code=403)
    result = verify_source("https://example.com/paywall", "Paywalled")
    assert result.action == "flagged"
    assert result.http_status == 403
    assert "access restricted" in result.reason.lower() or "paywall" in result.reason.lower()


@patch("wos.source_verification.requests.get")
def test_5xx(mock_get):
    mock_get.return_value = _mock_response(status_code=500)
    result = verify_source("https://example.com/broken", "Broken")
    assert result.action == "flagged"
    assert result.http_status == 500


@patch("wos.source_verification.requests.get")
def test_dns_failure(mock_get):
    mock_get.side_effect = requests.ConnectionError("DNS resolution failed")
    result = verify_source("https://nonexistent.example", "No DNS")
    assert result.action == "removed"
    assert result.http_status is None


@patch("wos.source_verification.requests.get")
def test_timeout(mock_get):
    mock_get.side_effect = requests.Timeout("Connection timed out")
    result = verify_source("https://slow.example", "Slow Site")
    assert result.action == "removed"
    assert result.http_status is None


@patch("wos.source_verification.requests.get")
def test_redirect_same_domain(mock_get):
    mock_get.return_value = _mock_response(
        text="<title>Redirected Page</title>",
        url="https://example.com/new-path",
    )
    result = verify_source("https://example.com/old-path", "Redirected Page")
    assert result.action == "ok"


@patch("wos.source_verification.requests.get")
def test_redirect_different_domain(mock_get):
    mock_get.return_value = _mock_response(
        text="<title>Other Site</title>",
        url="https://other-domain.com/page",
    )
    result = verify_source("https://example.com/page", "Some Page")
    assert result.action == "flagged"
    assert "redirect" in result.reason.lower()


@patch("wos.source_verification.requests.get")
def test_title_normalization_match(mock_get):
    mock_get.return_value = _mock_response(
        text="<title>PEP 8 \u2013 Style Guide for Python Code</title>",
        url="https://peps.python.org/pep-0008/",
    )
    result = verify_source("https://peps.python.org/pep-0008/", "PEP 8 Style Guide")
    assert result.action == "ok"
    assert result.title_match is True
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_source_verification.py::test_200_title_match -v`
Expected: FAIL — `ImportError: cannot import name 'VerificationResult'`

**Step 3: Write minimal implementation**

Add to `wos/source_verification.py`:

```python
import dataclasses
from urllib.parse import urlparse

import requests


@dataclasses.dataclass
class VerificationResult:
    """Result of verifying a single source URL."""

    url: str
    cited_title: str
    http_status: Optional[int]
    page_title: Optional[str]
    title_match: Optional[bool]
    action: str  # "ok" | "removed" | "flagged"
    reason: str


def verify_source(url: str, cited_title: str) -> VerificationResult:
    """Verify a single source URL. Returns a VerificationResult."""
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True)
    except requests.ConnectionError:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=None,
            page_title=None, title_match=None,
            action="removed", reason="Connection error (DNS failure or unreachable)",
        )
    except requests.Timeout:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=None,
            page_title=None, title_match=None,
            action="removed", reason="Connection timed out",
        )
    except requests.RequestException as exc:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=None,
            page_title=None, title_match=None,
            action="removed", reason=f"Request error: {exc}",
        )

    status = resp.status_code

    # Hard failures — source doesn't exist
    if status == 404:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=None, title_match=None,
            action="removed", reason="404 Not Found",
        )

    # Soft failures — source exists but access is restricted
    if status == 403:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=None, title_match=None,
            action="flagged", reason="403 Forbidden — paywall or access restricted",
        )

    if status >= 500:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=None, title_match=None,
            action="flagged", reason=f"{status} server error",
        )

    if status >= 400:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=None, title_match=None,
            action="removed", reason=f"{status} client error",
        )

    # Check for cross-domain redirect
    original_domain = urlparse(url).netloc
    final_domain = urlparse(resp.url).netloc
    if original_domain != final_domain:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=None, title_match=None,
            action="flagged",
            reason=f"Redirected to different domain: {resp.url}",
        )

    # Extract and compare title
    page_title = extract_page_title(resp.text)
    if page_title is None:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=None, title_match=None,
            action="ok", reason=f"{status} OK (no title to compare)",
        )

    match = titles_match(cited_title, page_title)
    if match:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=page_title, title_match=True,
            action="ok", reason=f"{status} OK, title matches",
        )
    else:
        return VerificationResult(
            url=url, cited_title=cited_title, http_status=status,
            page_title=page_title, title_match=False,
            action="flagged",
            reason=f"Title mismatch — cited: \"{cited_title}\", actual: \"{page_title}\"",
        )
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_source_verification.py -v`
Expected: All 27 tests PASS

**Step 5: Commit**

```bash
git add wos/source_verification.py tests/test_source_verification.py
git commit -m "feat: add single-source verification with VerificationResult"
```

---

### Task 5: Batch verification and summary

**Files:**
- Modify: `wos/source_verification.py`
- Modify: `tests/test_source_verification.py`

**Step 1: Write failing tests for `verify_sources` and `format_summary`**

Append to `tests/test_source_verification.py`:

```python
from wos.source_verification import format_summary, verify_sources


# ── Batch verification ──────────────────────────────────────────


@patch("wos.source_verification.requests.get")
def test_batch_mixed(mock_get):
    def side_effect(url, **kwargs):
        if "good" in url:
            return _mock_response(text="<title>Good Page</title>", url=url)
        elif "gone" in url:
            return _mock_response(status_code=404, url=url)
        elif "mismatch" in url:
            return _mock_response(text="<title>Wrong Title</title>", url=url)
        return _mock_response(url=url)

    mock_get.side_effect = side_effect

    sources = [
        {"url": "https://good.example/page", "title": "Good Page"},
        {"url": "https://gone.example/page", "title": "Gone Page"},
        {"url": "https://mismatch.example/page", "title": "Expected Title"},
    ]
    results = verify_sources(sources)
    assert len(results) == 3

    actions = [r.action for r in results]
    assert actions[0] == "ok"
    assert actions[1] == "removed"
    assert actions[2] == "flagged"


@patch("wos.source_verification.requests.get")
def test_batch_empty(mock_get):
    results = verify_sources([])
    assert results == []
    mock_get.assert_not_called()


# ── Summary formatting ──────────────────────────────────────────


def test_format_summary_counts():
    results = [
        VerificationResult("u1", "t1", 200, "t1", True, "ok", "ok"),
        VerificationResult("u2", "t2", 200, "t2", True, "ok", "ok"),
        VerificationResult("u3", "t3", 404, None, None, "removed", "404"),
        VerificationResult("u4", "t4", 200, "wrong", False, "flagged", "mismatch"),
    ]
    summary = format_summary(results)
    assert summary["total"] == 4
    assert summary["ok"] == 2
    assert summary["removed"] == 1
    assert summary["flagged"] == 1
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_source_verification.py::test_batch_mixed -v`
Expected: FAIL — `ImportError: cannot import name 'verify_sources'`

**Step 3: Write minimal implementation**

Add to `wos/source_verification.py`:

```python
def verify_sources(
    sources: list[dict],
) -> list[VerificationResult]:
    """Verify a batch of {url, title} sources. Returns one result per source."""
    results = []
    for source in sources:
        result = verify_source(source["url"], source["title"])
        results.append(result)
    return results


def format_summary(results: list[VerificationResult]) -> dict:
    """Compute summary counts from verification results."""
    counts = {"ok": 0, "removed": 0, "flagged": 0}
    for r in results:
        counts[r.action] = counts.get(r.action, 0) + 1
    return {"total": len(results), **counts}
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_source_verification.py -v`
Expected: All 30 tests PASS

**Step 5: Commit**

```bash
git add wos/source_verification.py tests/test_source_verification.py
git commit -m "feat: add batch source verification and summary formatting"
```

---

### Task 6: CLI entry point (`__main__`)

**Files:**
- Modify: `wos/source_verification.py`
- Modify: `tests/test_source_verification.py`

**Step 1: Write failing tests for CLI**

Append to `tests/test_source_verification.py`:

```python
import json
import subprocess
import sys


# ── CLI tests ───────────────────────────────────────────────────


@patch("wos.source_verification.requests.get")
def test_cli_json_output(mock_get):
    mock_get.return_value = _mock_response(
        text="<title>Test Page</title>",
        url="https://example.com",
    )
    input_json = json.dumps([{"url": "https://example.com", "title": "Test Page"}])
    proc = subprocess.run(
        [sys.executable, "-m", "wos.source_verification"],
        input=input_json,
        capture_output=True,
        text=True,
    )
    output = json.loads(proc.stdout)
    assert "results" in output
    assert "summary" in output
    assert output["summary"]["total"] == 1


@patch("wos.source_verification.requests.get")
def test_cli_exit_code_zero_when_all_ok(mock_get):
    mock_get.return_value = _mock_response(
        text="<title>OK Page</title>",
        url="https://example.com",
    )
    input_json = json.dumps([{"url": "https://example.com", "title": "OK Page"}])
    proc = subprocess.run(
        [sys.executable, "-m", "wos.source_verification"],
        input=input_json,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0


@patch("wos.source_verification.requests.get")
def test_cli_exit_code_one_when_removed(mock_get):
    mock_get.return_value = _mock_response(status_code=404)
    input_json = json.dumps([{"url": "https://example.com/gone", "title": "Gone"}])
    proc = subprocess.run(
        [sys.executable, "-m", "wos.source_verification"],
        input=input_json,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
```

**Important note on CLI tests:** The `subprocess.run` calls spawn a new process, so `@patch` on the test function won't affect the subprocess. These CLI tests will make real HTTP requests unless the module is refactored to support a test mode. There are two options:

**Option A (recommended):** Replace the subprocess-based CLI tests with tests that call the `main()` function directly, patching `sys.stdin` and `sys.stdout`:

```python
import io

from wos.source_verification import main


@patch("wos.source_verification.requests.get")
@patch("sys.stdin", new_callable=lambda: io.StringIO)
@patch("sys.stdout", new_callable=io.StringIO)
def test_cli_json_output(mock_stdout, mock_stdin, mock_get):
    mock_get.return_value = _mock_response(
        text="<title>Test Page</title>",
        url="https://example.com",
    )
    mock_stdin.return_value = io.StringIO(
        json.dumps([{"url": "https://example.com", "title": "Test Page"}])
    )
    try:
        main()
    except SystemExit:
        pass
    output = json.loads(mock_stdout.getvalue())
    assert "results" in output
    assert "summary" in output
    assert output["summary"]["total"] == 1
```

Use **Option A** for the actual implementation — test `main()` directly with mocked stdin/stdout/requests. The subprocess approach is shown above for clarity but won't work with `@patch`.

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_source_verification.py::test_cli_json_output -v`
Expected: FAIL — `ImportError: cannot import name 'main'`

**Step 3: Write minimal implementation**

Add to `wos/source_verification.py`:

```python
import json
import sys


def format_human_summary(results: list[VerificationResult]) -> str:
    """Format results as human-readable text for stderr."""
    lines = [f"Source verification ({len(results)} sources):"]
    for r in results:
        if r.action == "ok":
            lines.append(f"  \u2713 {r.url} \u2014 {r.reason}")
        elif r.action == "removed":
            lines.append(f"  \u2717 {r.url} \u2014 {r.reason} (REMOVED)")
        elif r.action == "flagged":
            lines.append(f"  \u26a0 {r.url} \u2014 {r.reason} (FLAGGED)")
    summary = format_summary(results)
    lines.append("")
    lines.append(
        f"Summary: {summary['ok']} ok, "
        f"{summary['removed']} removed, "
        f"{summary['flagged']} flagged"
    )
    return "\n".join(lines)


def main() -> None:
    """CLI entry point: read JSON from stdin, write results to stdout."""
    raw = sys.stdin.read()
    sources = json.loads(raw)
    results = verify_sources(sources)
    summary = format_summary(results)

    output = {
        "results": [dataclasses.asdict(r) for r in results],
        "summary": summary,
    }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")

    sys.stderr.write(format_human_summary(results) + "\n")

    has_removed = any(r.action == "removed" for r in results)
    sys.exit(1 if has_removed else 0)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_source_verification.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add wos/source_verification.py tests/test_source_verification.py
git commit -m "feat: add CLI entry point for source verification module"
```

---

### Task 7: Update research skill workflow

**Files:**
- Create: `skills/research/references/source-verification.md`
- Modify: `skills/research/references/research-investigate.md`

**Step 1: Create the source verification reference file**

Create `skills/research/references/source-verification.md`:

```markdown
# Source Verification Reference

Mechanical URL verification to catch hallucinated sources, dead links, and
title mismatches. Run this after gathering sources and before SIFT evaluation.

## When to Run

After Phase 2 (Initial Source Gathering) completes, before Phase 3 (Source
Evaluation). Every source collected during gathering must pass verification
before entering the SIFT pipeline.

## How to Run

1. Format your collected sources as a JSON array:

   ```json
   [
     {"url": "https://example.com/page", "title": "Page Title"},
     {"url": "https://other.com/article", "title": "Article Title"}
   ]
   ```

2. Pipe the JSON to the verification module:

   ```bash
   echo '[{"url": "...", "title": "..."}]' | python3 -m wos.source_verification
   ```

3. Read the JSON output from stdout. Each result has an `action` field:
   - `ok` — source verified, keep it
   - `removed` — source is dead (404, DNS failure, timeout), drop it
   - `flagged` — source has an issue (title mismatch, paywall, redirect), review it

## What to Do with Results

**`removed` sources:** Drop them from your source list. Do not include them
in the research document. Note in your investigation that N sources were
removed during verification.

**`flagged` sources with title mismatch:** The cited title doesn't match the
actual page title. Update the cited title to match the page title, or
investigate whether the source is actually relevant.

**`flagged` sources with redirect:** The URL redirected to a different domain.
Check if the redirected destination is still the intended source. Update the
URL if needed.

**`flagged` sources with 403/5xx:** The source exists but is temporarily
unavailable or paywalled. Keep the source but note the access issue.

**All sources removed:** If verification removes every source, stop and inform
the user. Do not proceed with empty sources — gather new ones instead.

## Example Output

```
Source verification (4 sources):
  ✓ https://peps.python.org/pep-0008/ — 200 OK, title matches
  ✓ https://effectivepython.com/ — 200 OK (no title to compare)
  ✗ https://fakeblog.example/post — 404 Not Found (REMOVED)
  ⚠ https://arxiv.org/abs/2509.21361 — Title mismatch —
      cited: "The Maximum Effective Context Window...",
      actual: "Context Is What You Need..." (FLAGGED)

Summary: 2 ok, 1 removed, 1 flagged
```
```

**Step 2: Update research-investigate.md to add Phase 2.5**

In `skills/research/references/research-investigate.md`, insert a new section
between Phase 2 and Phase 3. Renumber Phase 3 through Phase 6 to become
Phase 4 through Phase 7. The new section:

```markdown
## Phase 3: Verify Sources

Run mechanical URL verification on all gathered sources before SIFT evaluation.
See `references/source-verification.md` for full instructions.

1. Format all gathered sources as JSON: `[{"url": "...", "title": "..."}, ...]`
2. Run: `echo '<json>' | python3 -m wos.source_verification`
3. Review the results:
   - Remove sources with action `removed` from your list
   - For sources with action `flagged`: update cited titles if mismatched,
     note access issues for paywalled sources
4. If all sources were removed, gather new sources before proceeding
5. Report verification results to the user before continuing
```

Also update the quality checklist to include a verification item:

```markdown
- [ ] All sources passed URL verification (Phase 3)
```

**Step 3: Verify the skill files are well-formed**

Run: `python3 -m pytest tests/ -v`
Expected: All existing tests still PASS (skill files aren't tested by pytest,
but this confirms no regressions)

**Step 4: Commit**

```bash
git add skills/research/references/source-verification.md skills/research/references/research-investigate.md
git commit -m "feat: integrate source verification into research skill workflow"
```

---

### Task 8: Run full test suite and verify

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS, including new source verification tests

**Step 2: Test CLI manually**

Run: `echo '[{"url":"https://example.com","title":"Example Domain"}]' | python3 -m wos.source_verification`
Expected: JSON output with one result, human summary on stderr

**Step 3: Final commit (if any fixups needed)**

If any tests fail or code needs adjustment, fix and commit.

---

### Task 9: Create branch and PR

**Step 1: Verify all changes**

Run: `git log --oneline main..HEAD` to see all commits.

**Step 2: Create PR**

```bash
gh pr create \
  --title "feat: source URL verification pass in /wos:research" \
  --body "Closes #6

## Summary
- Adds wos/source_verification.py module with verify_sources() for batch URL checking
- Checks HTTP status, extracts <title>, compares to cited title via normalized substring matching
- CLI entry point: python3 -m wos.source_verification (JSON stdin → JSON stdout)
- Integrates into research skill workflow as Phase 3 (between gathering and SIFT evaluation)

## Test plan
- 30+ unit tests with mocked HTTP (no real network calls)
- Tests cover: 200/404/403/5xx, DNS failure, timeout, redirects, title matching, CLI I/O
"
```
