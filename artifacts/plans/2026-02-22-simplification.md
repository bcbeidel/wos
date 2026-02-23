# WOS Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 23-class DDD hierarchy with ~5 flat modules, 5 validation checks, and 6 skills.

**Architecture:** One `Document` dataclass parsed from YAML frontmatter. Auto-generated `_index.md` files for navigation. Marker-based AGENTS.md section. All validation in one module with 5 checks.

**Tech Stack:** Python 3.9, stdlib `dataclasses`, `pyyaml`, `requests`. Pydantic kept as dependency only for `wos/preferences.py` (unchanged). Tests via `pytest`.

**Design doc:** `artifacts/plans/2026-02-22-simplification-design.md`

**Branch:** `phase/simplification`

**PR:** https://github.com/bcbeidel/wos/pull/38

---

### Task 1: Branch Setup and Delete Old Code

**Files:**
- Delete: `wos/models/` (entire directory)
- Delete: `wos/auto_fix.py`, `wos/cross_validators.py`, `wos/discovery.py`, `wos/document_types.py`, `wos/scaffold.py`, `wos/templates.py`, `wos/token_budget.py`, `wos/validators.py`, `wos/formatting.py`
- Delete: `tests/models/` (entire directory except `test_source_verification.py` — move to `tests/`)
- Delete: `tests/test_auto_fix.py`, `tests/test_cross_validators.py`, `tests/test_discovery.py`, `tests/test_document_types.py`, `tests/test_formatting.py`, `tests/test_scaffold.py`, `tests/test_templates.py`, `tests/test_token_budget.py`, `tests/test_validators.py`, `tests/test_check_health_integration.py`, `tests/test_scan_context.py`
- Delete: `tests/builders.py`
- Delete: `scripts/check_health.py`, `scripts/run_auto_fix.py`, `scripts/run_discovery.py`, `scripts/run_scaffold.py`, `scripts/scan_context.py`
- Delete: `skills/create-context/`, `skills/create-document/`, `skills/discover/`, `skills/fix/`, `skills/update-context/`, `skills/update-document/`
- Keep: `wos/__init__.py`, `wos/source_verification.py`, `wos/preferences.py`
- Keep: `tests/test_source_verification.py`, `tests/test_preferences.py`
- Keep: `skills/audit/`, `skills/consider/`, `skills/preferences/`, `skills/report-issue/`, `skills/research/`
- Modify: `wos/__init__.py` — clear any re-exports that reference deleted modules

**Step 1: Create branch**

```bash
git checkout -b phase/simplification
```

**Step 2: Delete old wos/ modules**

```bash
rm -rf wos/models/
rm -f wos/auto_fix.py wos/cross_validators.py wos/discovery.py \
      wos/document_types.py wos/scaffold.py wos/templates.py \
      wos/token_budget.py wos/validators.py wos/formatting.py
```

**Step 3: Delete old tests**

Move `tests/models/test_source_verification.py` to `tests/` first, then delete the rest:

```bash
mv tests/models/test_source_verification.py tests/test_source_verification_models.py
rm -rf tests/models/
rm -f tests/builders.py
rm -f tests/test_auto_fix.py tests/test_cross_validators.py \
      tests/test_discovery.py tests/test_document_types.py \
      tests/test_formatting.py tests/test_scaffold.py \
      tests/test_templates.py tests/test_token_budget.py \
      tests/test_validators.py tests/test_check_health_integration.py \
      tests/test_scan_context.py
```

**Step 4: Delete old scripts**

```bash
rm -f scripts/check_health.py scripts/run_auto_fix.py \
      scripts/run_discovery.py scripts/run_scaffold.py \
      scripts/scan_context.py
```

**Step 5: Delete old skills**

```bash
rm -rf skills/create-context/ skills/create-document/ skills/discover/ \
       skills/fix/ skills/update-context/ skills/update-document/
```

**Step 6: Clean up wos/__init__.py**

Replace contents with:

```python
"""wos: Claude Code plugin for structured project context."""
```

**Step 7: Verify clean state**

```bash
python3 -m pytest tests/test_source_verification.py tests/test_preferences.py -v
```

Expected: Existing kept tests may fail due to import changes. Note any failures — they'll be fixed in later tasks if needed. The goal here is a clean deletion.

**Step 8: Commit**

```bash
git add -A
git commit -m "chore: delete old DDD hierarchy, validators, skills, and tests

Clean slate for simplification. Kept: source_verification.py,
preferences.py, and their tests. Kept skills: audit, consider,
preferences, report-issue, research."
```

---

### Task 2: Document Dataclass + parse_document()

**Files:**
- Create: `wos/document.py`
- Create: `tests/test_document.py`

**Step 1: Write the failing tests**

Create `tests/test_document.py`:

```python
"""Tests for wos.document — Document dataclass and parse_document()."""
from __future__ import annotations

import pytest

from wos.document import Document, parse_document


class TestDocument:
    """Test Document dataclass basics."""

    def test_create_minimal(self):
        doc = Document(
            path="context/auth/oauth.md",
            name="OAuth Flows",
            description="How OAuth works",
            content="# OAuth Flows\n\nSome content.",
        )
        assert doc.name == "OAuth Flows"
        assert doc.description == "How OAuth works"
        assert doc.type is None
        assert doc.sources == []
        assert doc.related == []
        assert doc.extra == {}

    def test_create_research(self):
        doc = Document(
            path="artifacts/research/2026-02-20-oauth.md",
            name="OAuth Research",
            description="Comparing OAuth providers",
            type="research",
            sources=["https://example.com/oauth"],
            content="# OAuth Research\n\nFindings.",
        )
        assert doc.type == "research"
        assert doc.sources == ["https://example.com/oauth"]

    def test_create_with_extra_fields(self):
        doc = Document(
            path="context/auth/oauth.md",
            name="OAuth",
            description="OAuth guide",
            extra={"status": "draft", "priority": 1},
            content="# OAuth",
        )
        assert doc.extra["status"] == "draft"
        assert doc.extra["priority"] == 1

    def test_create_with_related(self):
        doc = Document(
            path="context/auth/oauth.md",
            name="OAuth",
            description="OAuth guide",
            related=["context/auth/sessions.md", "artifacts/research/oauth.md"],
            content="# OAuth",
        )
        assert len(doc.related) == 2


class TestParseDocument:
    """Test parse_document() frontmatter extraction."""

    def test_parse_minimal(self):
        text = (
            "---\n"
            "name: OAuth Flows\n"
            "description: How OAuth works\n"
            "---\n"
            "# OAuth Flows\n"
            "\n"
            "Some content here.\n"
        )
        doc = parse_document("context/auth/oauth.md", text)
        assert doc.name == "OAuth Flows"
        assert doc.description == "How OAuth works"
        assert doc.type is None
        assert doc.sources == []
        assert doc.related == []
        assert doc.extra == {}
        assert "Some content here." in doc.content

    def test_parse_research_with_sources(self):
        text = (
            "---\n"
            "name: OAuth Research\n"
            "description: Comparing providers\n"
            "type: research\n"
            "sources:\n"
            "  - https://example.com/oauth\n"
            "  - https://example.com/oidc\n"
            "---\n"
            "# Research\n"
        )
        doc = parse_document("artifacts/research/oauth.md", text)
        assert doc.type == "research"
        assert len(doc.sources) == 2

    def test_parse_with_related(self):
        text = (
            "---\n"
            "name: OAuth\n"
            "description: Guide\n"
            "related:\n"
            "  - context/auth/sessions.md\n"
            "---\n"
            "# OAuth\n"
        )
        doc = parse_document("context/auth/oauth.md", text)
        assert doc.related == ["context/auth/sessions.md"]

    def test_parse_extra_fields_preserved(self):
        text = (
            "---\n"
            "name: OAuth\n"
            "description: Guide\n"
            "status: draft\n"
            "priority: 1\n"
            "tags:\n"
            "  - auth\n"
            "  - security\n"
            "---\n"
            "# OAuth\n"
        )
        doc = parse_document("context/auth/oauth.md", text)
        assert doc.extra["status"] == "draft"
        assert doc.extra["priority"] == 1
        assert doc.extra["tags"] == ["auth", "security"]

    def test_parse_no_frontmatter_raises(self):
        text = "# Just a heading\n\nNo frontmatter.\n"
        with pytest.raises(ValueError, match="frontmatter"):
            parse_document("file.md", text)

    def test_parse_missing_name_raises(self):
        text = (
            "---\n"
            "description: Has desc but no name\n"
            "---\n"
            "# Heading\n"
        )
        with pytest.raises(ValueError, match="name"):
            parse_document("file.md", text)

    def test_parse_missing_description_raises(self):
        text = (
            "---\n"
            "name: Has name but no desc\n"
            "---\n"
            "# Heading\n"
        )
        with pytest.raises(ValueError, match="description"):
            parse_document("file.md", text)

    def test_parse_content_excludes_frontmatter(self):
        text = (
            "---\n"
            "name: Test\n"
            "description: Test doc\n"
            "---\n"
            "# Heading\n"
            "\n"
            "Body text.\n"
        )
        doc = parse_document("file.md", text)
        assert "---" not in doc.content
        assert "name:" not in doc.content
        assert "# Heading" in doc.content
        assert "Body text." in doc.content

    def test_parse_empty_frontmatter_raises(self):
        text = "---\n---\n# Heading\n"
        with pytest.raises(ValueError, match="name"):
            parse_document("file.md", text)
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_document.py -v
```

Expected: `ModuleNotFoundError: No module named 'wos.document'`

**Step 3: Write minimal implementation**

Create `wos/document.py`:

```python
"""Document dataclass and frontmatter parser."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import yaml


# Fields extracted from frontmatter into dedicated Document attributes.
_KNOWN_FIELDS = {"name", "description", "type", "sources", "related"}


@dataclass
class Document:
    """A markdown document with YAML frontmatter metadata."""

    path: str
    name: str
    description: str
    content: str
    type: Optional[str] = None
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


def parse_document(path: str, text: str) -> Document:
    """Parse a markdown file into a Document.

    Extracts YAML frontmatter (between --- delimiters), pulls out known
    fields (name, description, type, sources, related), passes the rest
    into extra. Everything after the closing --- is content.

    Raises ValueError if frontmatter is missing or required fields absent.
    """
    # Split frontmatter from content
    if not text.startswith("---"):
        raise ValueError(f"{path}: no frontmatter found (file must start with ---)")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{path}: no frontmatter found (missing closing ---)")

    raw_frontmatter = parts[1]
    content = parts[2].lstrip("\n")

    # Parse YAML
    fm = yaml.safe_load(raw_frontmatter)
    if not isinstance(fm, dict):
        fm = {}

    # Validate required fields
    if "name" not in fm:
        raise ValueError(f"{path}: frontmatter missing required field 'name'")
    if "description" not in fm:
        raise ValueError(f"{path}: frontmatter missing required field 'description'")

    # Extract known fields, collect extras
    extra = {k: v for k, v in fm.items() if k not in _KNOWN_FIELDS}

    return Document(
        path=path,
        name=fm["name"],
        description=fm["description"],
        type=fm.get("type"),
        sources=fm.get("sources", []) or [],
        related=fm.get("related", []) or [],
        extra=extra,
        content=content,
    )
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_document.py -v
```

Expected: All 12 tests PASS.

**Step 5: Commit**

```bash
git add wos/document.py tests/test_document.py
git commit -m "feat: add Document dataclass and parse_document()

Single flat dataclass with name, description, type, sources, related,
and extra fields. parse_document() extracts YAML frontmatter."
```

---

### Task 3: URL Checker

**Files:**
- Create: `wos/url_checker.py`
- Create: `tests/test_url_checker.py`

Note: This is a simplified version of `wos/source_verification.py`. The existing
`source_verification.py` is kept alongside for now (the research skill may
reference it). We can clean up the overlap in Task 9.

**Step 1: Write the failing tests**

Create `tests/test_url_checker.py`:

```python
"""Tests for wos.url_checker — URL reachability checking."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from wos.url_checker import check_url, check_urls, UrlCheckResult


class TestUrlCheckResult:
    """Test UrlCheckResult dataclass."""

    def test_reachable(self):
        r = UrlCheckResult(url="https://example.com", status=200, reachable=True)
        assert r.reachable is True
        assert r.reason is None

    def test_unreachable(self):
        r = UrlCheckResult(
            url="https://gone.example.com",
            status=404,
            reachable=False,
            reason="Not Found",
        )
        assert r.reachable is False
        assert r.reason == "Not Found"


class TestCheckUrl:
    """Test check_url() with mocked HTTP."""

    @patch("wos.url_checker.requests.head")
    def test_reachable_200(self, mock_head):
        mock_head.return_value = MagicMock(status_code=200)
        result = check_url("https://example.com")
        assert result.reachable is True
        assert result.status == 200

    @patch("wos.url_checker.requests.head")
    def test_not_found_404(self, mock_head):
        mock_head.return_value = MagicMock(status_code=404)
        result = check_url("https://example.com/missing")
        assert result.reachable is False
        assert result.status == 404

    @patch("wos.url_checker.requests.get")
    @patch("wos.url_checker.requests.head")
    def test_head_405_falls_back_to_get(self, mock_head, mock_get):
        mock_head.return_value = MagicMock(status_code=405)
        mock_get.return_value = MagicMock(status_code=200)
        result = check_url("https://example.com")
        assert result.reachable is True
        assert result.status == 200
        mock_get.assert_called_once()

    @patch("wos.url_checker.requests.head")
    def test_connection_error(self, mock_head):
        mock_head.side_effect = Exception("Connection refused")
        result = check_url("https://unreachable.example.com")
        assert result.reachable is False
        assert result.status == 0
        assert "Connection refused" in result.reason

    @patch("wos.url_checker.requests.head")
    def test_timeout(self, mock_head):
        import requests as req
        mock_head.side_effect = req.Timeout("timed out")
        result = check_url("https://slow.example.com")
        assert result.reachable is False
        assert result.status == 0

    @patch("wos.url_checker.requests.head")
    def test_invalid_url_scheme(self, mock_head):
        result = check_url("ftp://example.com/file")
        assert result.reachable is False
        assert "http" in result.reason.lower()
        mock_head.assert_not_called()


class TestCheckUrls:
    """Test check_urls() batch function."""

    @patch("wos.url_checker.check_url")
    def test_batch_check(self, mock_check):
        mock_check.side_effect = [
            UrlCheckResult(url="https://a.com", status=200, reachable=True),
            UrlCheckResult(url="https://b.com", status=404, reachable=False, reason="Not Found"),
        ]
        results = check_urls(["https://a.com", "https://b.com"])
        assert len(results) == 2
        assert results[0].reachable is True
        assert results[1].reachable is False

    @patch("wos.url_checker.check_url")
    def test_empty_list(self, mock_check):
        results = check_urls([])
        assert results == []
        mock_check.assert_not_called()

    @patch("wos.url_checker.check_url")
    def test_deduplicates_urls(self, mock_check):
        mock_check.return_value = UrlCheckResult(
            url="https://a.com", status=200, reachable=True
        )
        results = check_urls(["https://a.com", "https://a.com", "https://a.com"])
        assert len(results) == 1
        mock_check.assert_called_once()
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_url_checker.py -v
```

Expected: `ModuleNotFoundError: No module named 'wos.url_checker'`

**Step 3: Write minimal implementation**

Create `wos/url_checker.py`:

```python
"""URL reachability checker — HTTP HEAD with GET fallback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests


_TIMEOUT = 10  # seconds
_USER_AGENT = "wos-url-checker/1.0"
_HEADERS = {"User-Agent": _USER_AGENT}


@dataclass
class UrlCheckResult:
    """Result of a URL reachability check."""

    url: str
    status: int
    reachable: bool
    reason: Optional[str] = None


def check_url(url: str) -> UrlCheckResult:
    """Check if a URL is reachable via HTTP HEAD, falling back to GET on 405.

    Returns UrlCheckResult with reachable=True for 2xx/3xx status codes.
    Non-HTTP URLs (ftp://, etc.) return reachable=False immediately.
    """
    if not url.startswith(("http://", "https://")):
        return UrlCheckResult(
            url=url, status=0, reachable=False,
            reason="Only http/https URLs are supported",
        )

    try:
        resp = requests.head(url, timeout=_TIMEOUT, headers=_HEADERS,
                             allow_redirects=True)
        # Some servers reject HEAD — fall back to GET
        if resp.status_code == 405:
            resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS,
                                allow_redirects=True, stream=True)

        reachable = resp.status_code < 400
        reason = None if reachable else f"HTTP {resp.status_code}"
        return UrlCheckResult(
            url=url, status=resp.status_code, reachable=reachable, reason=reason,
        )
    except Exception as exc:
        return UrlCheckResult(
            url=url, status=0, reachable=False, reason=str(exc),
        )


def check_urls(urls: list[str]) -> list[UrlCheckResult]:
    """Check multiple URLs, deduplicating."""
    seen: dict[str, UrlCheckResult] = {}
    for url in urls:
        if url not in seen:
            seen[url] = check_url(url)
    return list(seen.values())
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_url_checker.py -v
```

Expected: All 9 tests PASS.

**Step 5: Commit**

```bash
git add wos/url_checker.py tests/test_url_checker.py
git commit -m "feat: add url_checker module — HTTP HEAD/GET reachability

Simplified URL checking: HEAD with GET fallback on 405,
deduplication in batch mode."
```

---

### Task 4: Index Generator

**Files:**
- Create: `wos/index.py`
- Create: `tests/test_index.py`

**Step 1: Write the failing tests**

Create `tests/test_index.py`:

```python
"""Tests for wos.index — _index.md generation and sync checking."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from wos.index import generate_index, check_index_sync


@pytest.fixture
def tmp_context(tmp_path):
    """Create a temporary context directory with markdown files."""
    area = tmp_path / "authentication"
    area.mkdir()

    (area / "oauth.md").write_text(
        "---\nname: OAuth Flows\n"
        "description: How OAuth authorization works\n---\n# OAuth\n"
    )
    (area / "sessions.md").write_text(
        "---\nname: Session Management\n"
        "description: Server-side session handling\n---\n# Sessions\n"
    )
    # A subdirectory with its own _index.md
    sub = area / "advanced"
    sub.mkdir()
    (sub / "_index.md").write_text("# Advanced\n")
    (sub / "mfa.md").write_text(
        "---\nname: MFA\ndescription: Multi-factor authentication\n---\n# MFA\n"
    )
    return area


class TestGenerateIndex:
    """Test _index.md generation from directory contents."""

    def test_generates_file_table(self, tmp_context):
        content = generate_index(tmp_context)
        assert "| File | Description |" in content
        assert "[oauth.md](oauth.md)" in content
        assert "How OAuth authorization works" in content
        assert "[sessions.md](sessions.md)" in content
        assert "Server-side session handling" in content

    def test_generates_subdirectory_table(self, tmp_context):
        content = generate_index(tmp_context)
        assert "## Subdirectories" in content
        assert "[advanced/](advanced/)" in content

    def test_excludes_index_file(self, tmp_context):
        # Create an _index.md — it should not list itself
        (tmp_context / "_index.md").write_text("# Auth\n")
        content = generate_index(tmp_context)
        assert "_index.md" not in content.split("| File |")[1].split("## Subdirectories")[0]

    def test_sorted_alphabetically(self, tmp_context):
        content = generate_index(tmp_context)
        lines = content.split("\n")
        file_lines = [l for l in lines if l.startswith("| [") and ".md]" in l]
        names = [l.split("[")[1].split("]")[0] for l in file_lines]
        assert names == sorted(names)

    def test_heading_uses_directory_name(self, tmp_context):
        content = generate_index(tmp_context)
        assert content.startswith("# Authentication")

    def test_empty_directory(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        content = generate_index(empty)
        assert "# Empty" in content
        # No file table if no files
        assert "| File |" not in content

    def test_file_without_frontmatter_shows_no_description(self, tmp_path):
        d = tmp_path / "area"
        d.mkdir()
        (d / "plain.md").write_text("# Just a heading\n\nNo frontmatter.\n")
        content = generate_index(d)
        assert "[plain.md](plain.md)" in content
        assert "*(no description)*" in content

    def test_nested_index_generation(self, tmp_context):
        sub = tmp_context / "advanced"
        content = generate_index(sub)
        assert "# Advanced" in content
        assert "[mfa.md](mfa.md)" in content
        assert "Multi-factor authentication" in content


class TestCheckIndexSync:
    """Test index sync checking."""

    def test_in_sync(self, tmp_context):
        index_content = generate_index(tmp_context)
        (tmp_context / "_index.md").write_text(index_content)
        issues = check_index_sync(tmp_context)
        assert issues == []

    def test_missing_index(self, tmp_context):
        issues = check_index_sync(tmp_context)
        assert len(issues) == 1
        assert "missing" in issues[0]["issue"].lower()

    def test_stale_index_missing_file(self, tmp_context):
        index_content = generate_index(tmp_context)
        (tmp_context / "_index.md").write_text(index_content)
        # Add a new file after index generation
        (tmp_context / "new-topic.md").write_text(
            "---\nname: New\ndescription: New topic\n---\n# New\n"
        )
        issues = check_index_sync(tmp_context)
        assert len(issues) == 1
        assert "out of sync" in issues[0]["issue"].lower()

    def test_stale_index_extra_file(self, tmp_context):
        index_content = generate_index(tmp_context)
        (tmp_context / "_index.md").write_text(index_content)
        # Remove a file after index generation
        (tmp_context / "oauth.md").unlink()
        issues = check_index_sync(tmp_context)
        assert len(issues) == 1
        assert "out of sync" in issues[0]["issue"].lower()
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_index.py -v
```

Expected: `ModuleNotFoundError: No module named 'wos.index'`

**Step 3: Write minimal implementation**

Create `wos/index.py`:

```python
"""Index generator — auto-generates _index.md files from frontmatter."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


def _extract_description(file_path: Path) -> Optional[str]:
    """Extract description from a markdown file's YAML frontmatter."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    fm = yaml.safe_load(parts[1])
    if isinstance(fm, dict):
        return fm.get("description")
    return None


def _dir_display_name(path: Path) -> str:
    """Convert directory name to display name (capitalize, replace hyphens)."""
    return path.name.replace("-", " ").replace("_", " ").title()


def generate_index(directory: Path) -> str:
    """Generate _index.md content for a directory.

    Lists all .md files (except _index.md) with descriptions from their
    frontmatter. Lists subdirectories. Both sorted alphabetically.
    """
    directory = Path(directory)
    lines = [f"# {_dir_display_name(directory)}", ""]

    # Collect .md files (excluding _index.md)
    md_files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix == ".md" and f.name != "_index.md"
    )

    if md_files:
        lines.append("| File | Description |")
        lines.append("|------|-------------|")
        for f in md_files:
            desc = _extract_description(f) or "*(no description)*"
            lines.append(f"| [{f.name}]({f.name}) | {desc} |")
        lines.append("")

    # Collect subdirectories
    subdirs = sorted(d for d in directory.iterdir() if d.is_dir())

    if subdirs:
        lines.append("## Subdirectories")
        lines.append("")
        lines.append("| Directory | Description |")
        lines.append("|-----------|-------------|")
        for d in subdirs:
            sub_index = d / "_index.md"
            if sub_index.exists():
                desc = _extract_description(sub_index) or _dir_display_name(d)
            else:
                desc = _dir_display_name(d)
            lines.append(f"| [{d.name}/]({d.name}/) | {desc} |")
        lines.append("")

    return "\n".join(lines) + "\n"


def _current_file_set(directory: Path) -> set[str]:
    """Get the set of .md filenames in a directory (excluding _index.md)."""
    return {
        f.name for f in directory.iterdir()
        if f.is_file() and f.suffix == ".md" and f.name != "_index.md"
    }


def _indexed_file_set(index_path: Path) -> set[str]:
    """Extract filenames listed in an _index.md file table."""
    names = set()
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError:
        return names

    for line in text.split("\n"):
        # Match table rows like "| [filename.md](filename.md) | ... |"
        if line.startswith("| [") and ".md](" in line:
            name = line.split("[")[1].split("]")[0]
            if name != "_index.md":
                names.add(name)
    return names


def check_index_sync(directory: Path) -> list[dict]:
    """Check if _index.md is in sync with directory contents.

    Returns list of issue dicts with keys: file, issue, severity.
    """
    directory = Path(directory)
    index_path = directory / "_index.md"

    if not index_path.exists():
        return [{
            "file": str(index_path),
            "issue": "_index.md is missing",
            "severity": "fail",
        }]

    on_disk = _current_file_set(directory)
    in_index = _indexed_file_set(index_path)

    if on_disk != in_index:
        added = on_disk - in_index
        removed = in_index - on_disk
        details = []
        if added:
            details.append(f"not indexed: {', '.join(sorted(added))}")
        if removed:
            details.append(f"indexed but missing: {', '.join(sorted(removed))}")
        return [{
            "file": str(index_path),
            "issue": f"_index.md is out of sync ({'; '.join(details)})",
            "severity": "fail",
        }]

    return []
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_index.py -v
```

Expected: All 12 tests PASS.

**Step 5: Commit**

```bash
git add wos/index.py tests/test_index.py
git commit -m "feat: add index generator — auto-generated _index.md from frontmatter

Generates file tables with descriptions from YAML frontmatter.
Checks sync between _index.md and directory contents."
```

---

### Task 5: Validators

**Files:**
- Create: `wos/validators.py`
- Create: `tests/test_validators.py`

**Step 1: Write the failing tests**

Create `tests/test_validators.py`:

```python
"""Tests for wos.validators — 5 validation checks."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from wos.document import Document
from wos.validators import (
    check_frontmatter,
    check_research_sources,
    check_source_urls,
    check_related_paths,
    check_all_indexes,
    validate_file,
    validate_project,
)


class TestCheckFrontmatter:
    """Check 1: name and description present."""

    def test_valid_document_no_issues(self):
        doc = Document(path="f.md", name="Title", description="Desc", content="")
        assert check_frontmatter(doc) == []

    def test_empty_name(self):
        doc = Document(path="f.md", name="", description="Desc", content="")
        issues = check_frontmatter(doc)
        assert len(issues) == 1
        assert "name" in issues[0]["issue"].lower()

    def test_empty_description(self):
        doc = Document(path="f.md", name="Title", description="", content="")
        issues = check_frontmatter(doc)
        assert len(issues) == 1
        assert "description" in issues[0]["issue"].lower()


class TestCheckResearchSources:
    """Check 2: research documents have sources."""

    def test_research_with_sources_ok(self):
        doc = Document(
            path="f.md", name="R", description="D", type="research",
            sources=["https://example.com"], content="",
        )
        assert check_research_sources(doc) == []

    def test_research_without_sources_fails(self):
        doc = Document(
            path="f.md", name="R", description="D", type="research",
            sources=[], content="",
        )
        issues = check_research_sources(doc)
        assert len(issues) == 1
        assert "sources" in issues[0]["issue"].lower()

    def test_non_research_without_sources_ok(self):
        doc = Document(
            path="f.md", name="T", description="D", type="reference",
            sources=[], content="",
        )
        assert check_research_sources(doc) == []

    def test_no_type_without_sources_ok(self):
        doc = Document(path="f.md", name="T", description="D", content="")
        assert check_research_sources(doc) == []


class TestCheckSourceUrls:
    """Check 3: source URLs are reachable."""

    @patch("wos.validators.check_urls")
    def test_all_reachable(self, mock_check):
        from wos.url_checker import UrlCheckResult
        mock_check.return_value = [
            UrlCheckResult(url="https://a.com", status=200, reachable=True),
        ]
        doc = Document(
            path="f.md", name="R", description="D",
            sources=["https://a.com"], content="",
        )
        assert check_source_urls(doc) == []

    @patch("wos.validators.check_urls")
    def test_unreachable_url(self, mock_check):
        from wos.url_checker import UrlCheckResult
        mock_check.return_value = [
            UrlCheckResult(url="https://gone.com", status=404, reachable=False,
                          reason="HTTP 404"),
        ]
        doc = Document(
            path="f.md", name="R", description="D",
            sources=["https://gone.com"], content="",
        )
        issues = check_source_urls(doc)
        assert len(issues) == 1
        assert "https://gone.com" in issues[0]["issue"]

    @patch("wos.validators.check_urls")
    def test_no_sources_no_check(self, mock_check):
        doc = Document(path="f.md", name="T", description="D", content="")
        assert check_source_urls(doc) == []
        mock_check.assert_not_called()


class TestCheckRelatedPaths:
    """Check 4: related file paths exist on disk."""

    def test_existing_paths_ok(self, tmp_path):
        (tmp_path / "other.md").write_text("# Other\n")
        doc = Document(
            path="f.md", name="T", description="D",
            related=["other.md"], content="",
        )
        assert check_related_paths(doc, root=tmp_path) == []

    def test_missing_path_fails(self, tmp_path):
        doc = Document(
            path="f.md", name="T", description="D",
            related=["nonexistent.md"], content="",
        )
        issues = check_related_paths(doc, root=tmp_path)
        assert len(issues) == 1
        assert "nonexistent.md" in issues[0]["issue"]

    def test_urls_in_related_skipped(self, tmp_path):
        doc = Document(
            path="f.md", name="T", description="D",
            related=["https://example.com/docs"], content="",
        )
        assert check_related_paths(doc, root=tmp_path) == []

    def test_no_related_no_issues(self, tmp_path):
        doc = Document(path="f.md", name="T", description="D", content="")
        assert check_related_paths(doc, root=tmp_path) == []


class TestCheckAllIndexes:
    """Check 5: _index.md files match directory contents."""

    def test_synced_index(self, tmp_path):
        from wos.index import generate_index
        area = tmp_path / "context" / "auth"
        area.mkdir(parents=True)
        (area / "oauth.md").write_text(
            "---\nname: OAuth\ndescription: OAuth guide\n---\n# OAuth\n"
        )
        (area / "_index.md").write_text(generate_index(area))
        issues = check_all_indexes(tmp_path / "context")
        assert issues == []

    def test_missing_index(self, tmp_path):
        area = tmp_path / "context" / "auth"
        area.mkdir(parents=True)
        (area / "oauth.md").write_text(
            "---\nname: OAuth\ndescription: OAuth guide\n---\n# OAuth\n"
        )
        issues = check_all_indexes(tmp_path / "context")
        assert len(issues) >= 1
        assert any("missing" in i["issue"].lower() for i in issues)


class TestValidateFile:
    """Test validate_file() — runs checks 1-4 on a single file."""

    def test_valid_file(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("---\nname: Doc\ndescription: A document\n---\n# Doc\n")
        issues = validate_file(f, root=tmp_path, check_urls=False)
        assert issues == []

    def test_invalid_file(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# No frontmatter\n")
        issues = validate_file(f, root=tmp_path, check_urls=False)
        assert len(issues) >= 1


class TestValidateProject:
    """Test validate_project() — runs all 5 checks across a project."""

    def test_valid_project(self, tmp_path):
        from wos.index import generate_index
        ctx = tmp_path / "context" / "auth"
        ctx.mkdir(parents=True)
        (ctx / "oauth.md").write_text(
            "---\nname: OAuth\ndescription: OAuth flows\n---\n# OAuth\n"
        )
        (ctx / "_index.md").write_text(generate_index(ctx))
        ctx_root = tmp_path / "context"
        (ctx_root / "_index.md").write_text(generate_index(ctx_root))
        issues = validate_project(tmp_path, check_urls=False)
        assert issues == []
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_validators.py -v
```

Expected: `ModuleNotFoundError: No module named 'wos.validators'`

**Step 3: Write minimal implementation**

Create `wos/validators.py`:

```python
"""Validators — 5 checks for WOS project health."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from wos.document import Document, parse_document
from wos.index import check_index_sync
from wos.url_checker import check_urls


def check_frontmatter(doc: Document) -> list[dict]:
    """Check 1: name and description are present and non-empty."""
    issues = []
    if not doc.name.strip():
        issues.append({
            "file": doc.path,
            "issue": "Frontmatter 'name' is empty",
            "severity": "fail",
        })
    if not doc.description.strip():
        issues.append({
            "file": doc.path,
            "issue": "Frontmatter 'description' is empty",
            "severity": "fail",
        })
    return issues


def check_research_sources(doc: Document) -> list[dict]:
    """Check 2: research documents have a non-empty sources list."""
    if doc.type == "research" and not doc.sources:
        return [{
            "file": doc.path,
            "issue": "Research document has no sources",
            "severity": "fail",
        }]
    return []


def check_source_urls(doc: Document) -> list[dict]:
    """Check 3: all URLs in sources are reachable."""
    if not doc.sources:
        return []
    results = check_urls(doc.sources)
    issues = []
    for r in results:
        if not r.reachable:
            reason = f" ({r.reason})" if r.reason else ""
            issues.append({
                "file": doc.path,
                "issue": f"Source URL unreachable: {r.url}{reason}",
                "severity": "fail",
            })
    return issues


def check_related_paths(doc: Document, root: Path) -> list[dict]:
    """Check 4: file paths in related exist on disk. URLs are skipped."""
    issues = []
    for ref in doc.related:
        if ref.startswith(("http://", "https://")):
            continue
        full_path = root / ref
        if not full_path.exists():
            issues.append({
                "file": doc.path,
                "issue": f"Related path does not exist: {ref}",
                "severity": "fail",
            })
    return issues


def check_all_indexes(directory: Path) -> list[dict]:
    """Check 5: all _index.md files under directory are in sync.

    Walks the directory tree and checks each directory that contains
    .md files.
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    issues = []
    issues.extend(check_index_sync(directory))
    for sub in sorted(directory.iterdir()):
        if sub.is_dir():
            issues.extend(check_all_indexes(sub))
    return issues


def validate_file(
    path: Path,
    root: Path,
    check_urls: bool = True,
) -> list[dict]:
    """Run checks 1-4 on a single file."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [{"file": str(path), "issue": f"Cannot read: {exc}", "severity": "fail"}]

    try:
        doc = parse_document(str(path), text)
    except ValueError as exc:
        return [{"file": str(path), "issue": str(exc), "severity": "fail"}]

    issues = []
    issues.extend(check_frontmatter(doc))
    issues.extend(check_research_sources(doc))
    if check_urls:
        issues.extend(check_source_urls(doc))
    issues.extend(check_related_paths(doc, root))
    return issues


def validate_project(
    root: Path,
    check_urls: bool = True,
) -> list[dict]:
    """Run all 5 checks across a project."""
    root = Path(root)
    issues = []

    # Find all .md files under context/ and artifacts/
    for subdir_name in ("context", "artifacts"):
        subdir = root / subdir_name
        if not subdir.exists():
            continue
        # Check 5: index sync
        issues.extend(check_all_indexes(subdir))
        # Checks 1-4: per-file
        for md_file in sorted(subdir.rglob("*.md")):
            if md_file.name == "_index.md":
                continue
            issues.extend(validate_file(md_file, root, check_urls=check_urls))

    return issues
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_validators.py -v
```

Expected: All 17 tests PASS.

**Step 5: Commit**

```bash
git add wos/validators.py tests/test_validators.py
git commit -m "feat: add validators — 5 checks for project health

1. frontmatter name+description, 2. research sources required,
3. source URLs reachable, 4. related paths exist, 5. index sync."
```

---

### Task 6: AGENTS.md Manager

**Files:**
- Create: `wos/agents_md.py`
- Create: `tests/test_agents_md.py`

**Step 1: Write the failing tests**

Create `tests/test_agents_md.py`:

```python
"""Tests for wos.agents_md — marker-based AGENTS.md section management."""
from __future__ import annotations

import pytest

from wos.agents_md import (
    render_wos_section,
    update_agents_md,
    BEGIN_MARKER,
    END_MARKER,
)


class TestRenderWosSection:
    """Test WOS section rendering."""

    def test_renders_with_areas(self):
        areas = [
            {"name": "Authentication", "path": "context/authentication/"},
            {"name": "Deployment", "path": "context/deployment/"},
        ]
        section = render_wos_section(areas=areas)
        assert BEGIN_MARKER in section
        assert END_MARKER in section
        assert "Authentication" in section
        assert "context/authentication/" in section
        assert "context/_index.md" in section

    def test_renders_with_preferences(self):
        prefs = ["Be direct and concise", "Code over prose"]
        section = render_wos_section(areas=[], preferences=prefs)
        assert "### Preferences" in section
        assert "- Be direct and concise" in section
        assert "- Code over prose" in section

    def test_renders_without_preferences(self):
        section = render_wos_section(areas=[], preferences=None)
        assert "### Preferences" not in section

    def test_renders_metadata_format(self):
        section = render_wos_section(areas=[])
        assert "name:" in section
        assert "description:" in section
        assert "sources:" in section

    def test_renders_lost_in_middle_cue(self):
        section = render_wos_section(areas=[])
        assert "key insights first and last" in section


class TestUpdateAgentsMd:
    """Test marker-based content replacement."""

    def test_replace_existing_section(self):
        existing = (
            "# AGENTS.md\n\nSome intro.\n\n"
            f"{BEGIN_MARKER}\nold content\n{END_MARKER}\n\n"
            "Other stuff.\n"
        )
        result = update_agents_md(existing, areas=[], preferences=None)
        assert "old content" not in result
        assert BEGIN_MARKER in result
        assert END_MARKER in result
        assert "Some intro." in result
        assert "Other stuff." in result

    def test_append_when_no_markers(self):
        existing = "# AGENTS.md\n\nSome intro.\n"
        result = update_agents_md(existing, areas=[], preferences=None)
        assert BEGIN_MARKER in result
        assert END_MARKER in result
        assert "Some intro." in result

    def test_preserves_content_outside_markers(self):
        existing = (
            "# My Project\n\nCustom instructions.\n\n"
            f"{BEGIN_MARKER}\nold\n{END_MARKER}\n\n"
            "## Other Section\n\nKeep this.\n"
        )
        result = update_agents_md(existing, areas=[], preferences=None)
        assert "Custom instructions." in result
        assert "Keep this." in result

    def test_areas_appear_in_output(self):
        existing = f"{BEGIN_MARKER}\n{END_MARKER}\n"
        areas = [{"name": "Auth", "path": "context/auth/"}]
        result = update_agents_md(existing, areas=areas)
        assert "Auth" in result
        assert "context/auth/" in result

    def test_preferences_preserved(self):
        existing = f"{BEGIN_MARKER}\n{END_MARKER}\n"
        prefs = ["Be brief"]
        result = update_agents_md(existing, areas=[], preferences=prefs)
        assert "- Be brief" in result
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_agents_md.py -v
```

Expected: `ModuleNotFoundError: No module named 'wos.agents_md'`

**Step 3: Write minimal implementation**

Create `wos/agents_md.py`:

```python
"""AGENTS.md section manager — marker-based content injection."""
from __future__ import annotations

from typing import Optional

BEGIN_MARKER = "<!-- wos:begin -->"
END_MARKER = "<!-- wos:end -->"


def render_wos_section(
    areas: list[dict],
    preferences: Optional[list[str]] = None,
) -> str:
    """Render the WOS-managed section for AGENTS.md.

    Args:
        areas: list of dicts with 'name' and 'path' keys.
        preferences: optional list of preference strings.
    """
    lines = [
        BEGIN_MARKER,
        "## Context Navigation",
        "",
        "Each directory has an `_index.md` listing all files with descriptions.",
        "- `context/_index.md` -- all topic areas",
        "- `artifacts/_index.md` -- research & plans",
        "",
        "Each `.md` file starts with YAML metadata (between `---` lines).",
        "Read the `description` field before reading the full file.",
        "Documents put key insights first and last; supplemental detail in the middle.",
    ]

    if areas:
        lines.extend([
            "",
            "### Areas",
            "| Area | Path |",
            "|------|------|",
        ])
        for area in areas:
            lines.append(f"| {area['name']} | {area['path']} |")

    lines.extend([
        "",
        "### File Metadata Format",
        "```yaml",
        "---",
        "name: Title",
        "description: What this covers",
        "type: research       # optional",
        "sources: []          # required if type is research",
        "related: []          # optional, file paths from project root",
        "---",
        "```",
    ])

    if preferences:
        lines.extend([
            "",
            "### Preferences",
        ])
        for pref in preferences:
            lines.append(f"- {pref}")

    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


def update_agents_md(
    content: str,
    areas: list[dict],
    preferences: Optional[list[str]] = None,
) -> str:
    """Update the WOS section in AGENTS.md content.

    Replaces content between markers. If markers don't exist, appends
    the section at the end.
    """
    new_section = render_wos_section(areas, preferences)

    if BEGIN_MARKER in content and END_MARKER in content:
        before = content[: content.index(BEGIN_MARKER)]
        after = content[content.index(END_MARKER) + len(END_MARKER) :]
        return before + new_section + after
    else:
        # Append
        separator = "\n\n" if content and not content.endswith("\n\n") else ""
        if content and not content.endswith("\n"):
            separator = "\n\n"
        return content + separator + new_section
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_agents_md.py -v
```

Expected: All 10 tests PASS.

**Step 5: Commit**

```bash
git add wos/agents_md.py tests/test_agents_md.py
git commit -m "feat: add agents_md manager — marker-based AGENTS.md section

Renders navigation, areas table, metadata format, preferences.
Replaces between markers or appends if markers absent."
```

---

### Task 7: CLI Scripts

**Files:**
- Create: `scripts/audit.py`
- Create: `scripts/reindex.py`

Note: `scripts/create.py` is not needed — the `/wos:create` skill handles
creation via the LLM, not a CLI script. The CLI scripts are for automation
and CI.

**Step 1: Write `scripts/audit.py`**

```python
#!/usr/bin/env python3
"""Run WOS validation checks on a project.

Usage:
    python3 scripts/audit.py [--root DIR] [--no-urls] [--json] [--fix]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Validate WOS project health.")
    parser.add_argument("--root", default=".", help="Project root (default: CWD)")
    parser.add_argument("--no-urls", action="store_true",
                        help="Skip URL reachability checks")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--fix", action="store_true",
                        help="Auto-fix: regenerate out-of-sync _index.md files")
    args = parser.parse_args()

    from wos.validators import validate_project
    from wos.index import generate_index

    root = Path(args.root).resolve()
    issues = validate_project(root, check_urls=not args.no_urls)

    if args.fix:
        # Regenerate any out-of-sync indexes
        fixed = []
        remaining = []
        for issue in issues:
            if "out of sync" in issue["issue"].lower() or "missing" in issue["issue"].lower():
                index_path = Path(issue["file"])
                if index_path.name == "_index.md":
                    directory = index_path.parent
                else:
                    directory = index_path.parent
                content = generate_index(directory)
                (directory / "_index.md").write_text(content, encoding="utf-8")
                fixed.append(issue["file"])
            else:
                remaining.append(issue)
        if fixed:
            print(f"Fixed {len(fixed)} index file(s):", file=sys.stderr)
            for f in fixed:
                print(f"  {f}", file=sys.stderr)
        issues = remaining

    if args.json:
        print(json.dumps(issues, indent=2))
    else:
        if not issues:
            print("All checks passed.")
        else:
            for issue in issues:
                severity = issue["severity"].upper()
                print(f"[{severity}] {issue['file']}: {issue['issue']}")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
```

**Step 2: Write `scripts/reindex.py`**

```python
#!/usr/bin/env python3
"""Regenerate all _index.md files in a WOS project.

Usage:
    python3 scripts/reindex.py [--root DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _reindex_tree(directory: Path) -> int:
    """Recursively regenerate _index.md files. Returns count of files written."""
    from wos.index import generate_index

    count = 0
    # Only reindex directories that contain .md files or subdirectories
    md_files = [f for f in directory.iterdir()
                if f.is_file() and f.suffix == ".md" and f.name != "_index.md"]
    subdirs = [d for d in directory.iterdir() if d.is_dir()]

    if md_files or subdirs:
        content = generate_index(directory)
        index_path = directory / "_index.md"
        index_path.write_text(content, encoding="utf-8")
        print(f"  {index_path}")
        count += 1

    for sub in sorted(subdirs):
        count += _reindex_tree(sub)

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate all _index.md files."
    )
    parser.add_argument("--root", default=".", help="Project root (default: CWD)")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    total = 0
    for subdir_name in ("context", "artifacts"):
        subdir = root / subdir_name
        if subdir.exists():
            total += _reindex_tree(subdir)

    if total:
        print(f"\nRegenerated {total} _index.md file(s).")
    else:
        print("No context/ or artifacts/ directories found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 3: Verify scripts parse correctly**

```bash
python3 scripts/audit.py --help
python3 scripts/reindex.py --help
```

Expected: Both print help text without errors.

**Step 4: Commit**

```bash
git add scripts/audit.py scripts/reindex.py
git commit -m "feat: add CLI scripts — audit.py and reindex.py

audit.py runs 5 validation checks with --fix and --json options.
reindex.py regenerates all _index.md files."
```

---

### Task 8: Skills

**Files:**
- Create: `skills/create/SKILL.md` (+ `references/` if needed)
- Modify: `skills/audit/SKILL.md` (simplify to match new validator)
- Modify: `skills/research/SKILL.md` (update frontmatter references, add lost-in-the-middle guidance)

Skills that are unchanged: `consider`, `report-issue`, `preferences`.

**Step 1: Create `/wos:create` skill**

Create `skills/create/SKILL.md`:

```markdown
---
name: create
description: Create project context, areas, or documents
user-invocable: false
disable-model-invocation: true
---

# Create

Create and initialize structured project context.

## Routing

Determine user intent from their message:

1. **Initialize project** — "set up context", "initialize", "create context"
2. **Add area** — "add area for X", "new area", "create area"
3. **Create document** — "create a doc about X", "write about X", "new document"

## 1. Initialize Project

Create directory structure and AGENTS.md:

```
context/
  _index.md
artifacts/
  _index.md
  research/
    _index.md
  plans/
    _index.md
AGENTS.md (with WOS section)
```

Run: `python3 scripts/reindex.py --root .`

Update AGENTS.md with the WOS section using markers.

## 2. Add Area

1. Ask for area name (lowercase-hyphenated)
2. Create `context/{area}/`
3. Run `python3 scripts/reindex.py --root .`
4. Update AGENTS.md areas table

## 3. Create Document

1. Ask the user what the document should cover
2. Determine appropriate location (`context/{area}/` or `artifacts/research/` or `artifacts/plans/`)
3. Generate YAML frontmatter:
   - `name` and `description` (required)
   - `type` if appropriate (research, plan, reference, etc.)
   - `sources` if type is research (verify URLs with `python3 -c "from wos.url_checker import check_url; print(check_url('URL'))"`)
   - `related` if sourced from other project documents
4. Write document content following the lost-in-the-middle convention:
   - Top: summary with key insights and actionable guidance
   - Middle: detailed explanation, examples, context for human readers
   - Bottom: key takeaways or quick-reference summary
5. Run `python3 scripts/reindex.py --root .`

## Document Structure Convention

**LLMs lose attention in the middle of long documents.** Structure files so that:
- The top contains a summary with key insights and actionable guidance
- The middle contains detailed explanation, examples, and context for human readers
- The bottom restates key takeaways or provides a quick-reference summary

The first and last sections are what an agent is most likely to retain. Write for that.
```

**Step 2: Rewrite `/wos:audit` skill**

Read the current `skills/audit/SKILL.md` and rewrite to match the new 5-check system. The new version should reference `scripts/audit.py` and describe the 5 checks.

Replace `skills/audit/SKILL.md` with:

```markdown
---
name: audit
description: Validate project context health
user-invocable: true
---

# Audit

Run validation checks on the project's structured context.

## Checks

1. **Frontmatter** — every `.md` file (except `_index.md`) has `name` and `description`
2. **Research sources** — documents with `type: research` have a non-empty `sources` list
3. **Source URLs** — all URLs in `sources` are programmatically reachable
4. **Related paths** — file paths in `related` frontmatter exist on disk
5. **Index sync** — each `_index.md` matches its directory contents

## Running

```bash
python3 scripts/audit.py --root .
```

Options:
- `--no-urls` — skip URL reachability checks (faster)
- `--json` — output results as JSON
- `--fix` — regenerate out-of-sync `_index.md` files

## Interpreting Results

- No output + exit 0 = all checks passed
- `[FAIL]` lines + exit 1 = issues found

## Fixing Issues

- **Missing/empty frontmatter:** Add `name` and `description` to the file's YAML header
- **Missing sources on research:** Add `sources:` list with URLs to frontmatter
- **Unreachable URLs:** Verify the URL manually, update or remove if dead
- **Broken related paths:** Fix the path or remove the entry
- **Index out of sync:** Run `python3 scripts/reindex.py --root .` or use `--fix`
```

**Step 3: Update `/wos:research` skill**

Read `skills/research/SKILL.md`. Add the lost-in-the-middle document structure
guidance to the output format section. Update frontmatter references to use
`name`/`description`/`type: research`/`sources` instead of the old format.

The changes are targeted — keep the SIFT framework and source verification
workflow, just update the output document format section.

**Step 4: Delete old skill references/ directories that reference deleted code**

Check `skills/audit/references/` and remove any files that reference the old
validator system, health report, or formatting modules.

**Step 5: Commit**

```bash
git add skills/
git commit -m "feat: add /wos:create skill, simplify audit and research skills

create skill handles project init, areas, and documents.
audit skill references new 5-check system.
research skill updated with new frontmatter format."
```

---

### Task 9: CLAUDE.md, pyproject.toml, and Final Cleanup

**Files:**
- Modify: `CLAUDE.md`
- Modify: `pyproject.toml` (if dependency changes needed)
- Modify: `wos/__init__.py`
- Delete: `wos/source_verification.py` (if fully replaced by url_checker.py)
- Possibly modify: `wos/preferences.py` (check for broken imports)

**Step 1: Check for broken imports in kept files**

```bash
python3 -c "import wos.preferences"
python3 -c "import wos.source_verification"
```

Fix any import errors in `wos/preferences.py` and `wos/source_verification.py`
that reference deleted modules (e.g., imports from `wos.models.core`).

**Step 2: Decide on source_verification.py**

If `wos/url_checker.py` covers all needs and no skill directly calls
`source_verification.py`, delete it and its test. If the research skill
references it, keep it or update the skill to use `url_checker` instead.

**Step 3: Update CLAUDE.md**

Rewrite the Architecture, Package Structure, Domain Model, and Conventions
sections to reflect the simplified system. Key changes:

- Package structure: `wos/document.py`, `wos/index.py`, `wos/validators.py`,
  `wos/url_checker.py`, `wos/agents_md.py`
- Scripts: `scripts/audit.py`, `scripts/reindex.py`
- Skills: 6 total (create, audit, research, consider, report-issue, preferences)
- Remove all DDD references, section specs, document type hierarchy
- Update Build & Test section if needed

**Step 4: Run full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: All tests pass. Fix any remaining failures.

**Step 5: Run ruff lint**

```bash
ruff check wos/ tests/ scripts/
```

Fix any lint issues.

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: update CLAUDE.md and clean up for simplified architecture

Reflects new flat package structure, 5 validation checks, 6 skills."
```

**Step 7: Update design doc with branch and PR info**

Update `artifacts/plans/2026-02-22-simplification-design.md` header with branch
name and PR number once created.

---

## Summary

| Task | What | New Files | Tests |
|------|------|-----------|-------|
| 1 | Delete old code | — | — |
| 2 | Document dataclass | `wos/document.py` | 12 tests |
| 3 | URL checker | `wos/url_checker.py` | 9 tests |
| 4 | Index generator | `wos/index.py` | 12 tests |
| 5 | Validators | `wos/validators.py` | 17 tests |
| 6 | AGENTS.md manager | `wos/agents_md.py` | 10 tests |
| 7 | CLI scripts | `scripts/audit.py`, `scripts/reindex.py` | — |
| 8 | Skills | `skills/create/SKILL.md` + updates | — |
| 9 | Cleanup | CLAUDE.md updates | — |

**Total: ~60 new tests, ~5 source files, ~2 CLI scripts, 6 skills.**

Down from: 23 classes, 8,500 lines of tests, 5,600 lines of source, 11 skills.
