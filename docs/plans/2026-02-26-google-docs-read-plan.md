---
name: Google Docs Read Implementation Plan
description: Step-by-step implementation plan for Google Docs read integration
type: plan
related:
  - docs/plans/2026-02-26-google-docs-read-design.md
  - docs/research/2026-02-24-google-apis-research.md
---

# Google Docs Read Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable WOS to read Google Docs content as markdown, both for live reading and ingestion into context files.

**Architecture:** Pure logic (URL parsing, JSON-to-markdown extraction) lives in `wos/google_docs.py` (stdlib-only, fully testable). A thin PEP 723 CLI script at `scripts/google_docs.py` handles auth and API calls, importing the pure logic. A `/wos:read` skill orchestrates both.

**Tech Stack:** Python 3.9+, google-api-python-client (via PEP 723 inline deps), pytest

**Prerequisite:** Issue #70 (reliable uv run invocation) must be completed before the skill (Task 8) can work end-to-end. Tasks 1-7 can proceed independently.

**Branch:** `feat/google-docs-read`
**Pull Request:** TBD

---

### Task 1: Script skeleton and module scaffold

**Files:**
- Create: `wos/google_docs.py`
- Create: `scripts/google_docs.py`
- Test: `tests/test_google_docs.py`

**Step 1: Create the pure logic module**

Create `wos/google_docs.py` with module docstring and imports only:

```python
"""Google Docs text extraction and URL parsing (stdlib-only)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def parse_doc_url(url_or_id: str) -> str:
    """Extract a Google Docs document ID from a URL or raw ID.

    Accepts:
        - https://docs.google.com/document/d/DOCUMENT_ID/edit
        - https://docs.google.com/document/d/DOCUMENT_ID/edit#heading=h.xxx
        - https://docs.google.com/document/d/DOCUMENT_ID/
        - https://docs.google.com/document/d/DOCUMENT_ID
        - Raw document ID string

    Returns:
        The document ID string.

    Raises:
        ValueError: If the URL format is not recognized.
    """
    raise NotImplementedError


def extract_text(doc: Dict[str, Any]) -> str:
    """Convert a Google Docs API response to markdown.

    Args:
        doc: The full JSON response from documents.get().

    Returns:
        Markdown string of the document content.
    """
    raise NotImplementedError
```

**Step 2: Create the PEP 723 CLI script**

Create `scripts/google_docs.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "google-api-python-client>=2.0",
#   "google-auth-oauthlib>=1.0",
# ]
# ///
"""Read Google Docs content as markdown.

Usage:
    uv run scripts/google_docs.py auth [--force] [--client-secret PATH] [--check]
    uv run scripts/google_docs.py read <doc-url> [--json]
    uv run scripts/google_docs.py list [--limit N] [--query TEXT]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for wos imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CONFIG_DIR = Path(os.path.expanduser("~/.config/wos"))
TOKEN_PATH = CONFIG_DIR / "google-token.json"
CLIENT_SECRET_PATH = CONFIG_DIR / "google-client-secret.json"

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read Google Docs content as markdown."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # auth
    auth_p = sub.add_parser("auth", help="Set up Google OAuth credentials")
    auth_p.add_argument("--force", action="store_true", help="Re-authenticate even if token exists")
    auth_p.add_argument("--client-secret", type=str, help="Path to client secret JSON")
    auth_p.add_argument("--check", action="store_true", help="Check auth status silently")

    # read
    read_p = sub.add_parser("read", help="Read a Google Doc as markdown")
    read_p.add_argument("url", help="Google Docs URL or document ID")
    read_p.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")

    # list
    list_p = sub.add_parser("list", help="List recent Google Docs")
    list_p.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    list_p.add_argument("--query", type=str, help="Search by title")

    args = parser.parse_args()

    if args.command == "auth":
        cmd_auth(args)
    elif args.command == "read":
        cmd_read(args)
    elif args.command == "list":
        cmd_list(args)


def cmd_auth(args: argparse.Namespace) -> None:
    print("auth: not yet implemented", file=sys.stderr)
    sys.exit(1)


def cmd_read(args: argparse.Namespace) -> None:
    print("read: not yet implemented", file=sys.stderr)
    sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    print("list: not yet implemented", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 3: Create test file skeleton**

Create `tests/test_google_docs.py`:

```python
"""Tests for wos/google_docs.py — URL parsing and text extraction."""

from __future__ import annotations


class TestParseDocUrl:
    pass


class TestExtractText:
    pass
```

**Step 4: Verify everything imports**

Run: `uv run python -c "from wos.google_docs import parse_doc_url, extract_text; print('ok')"`
Expected: `ok`

Run: `uv run python -m pytest tests/test_google_docs.py -v`
Expected: `no tests ran` (0 collected)

**Step 5: Commit**

```bash
git add wos/google_docs.py scripts/google_docs.py tests/test_google_docs.py
git commit -m "feat: scaffold google docs script and module"
```

---

### Task 2: URL parsing — test + implement

**Files:**
- Modify: `wos/google_docs.py`
- Modify: `tests/test_google_docs.py`

**Step 1: Write the failing tests**

Add to `tests/test_google_docs.py` inside `TestParseDocUrl`:

```python
class TestParseDocUrl:
    def test_full_edit_url(self) -> None:
        from wos.google_docs import parse_doc_url

        url = "https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit"
        assert parse_doc_url(url) == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"

    def test_url_with_fragment(self) -> None:
        from wos.google_docs import parse_doc_url

        url = "https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit#heading=h.abc123"
        assert parse_doc_url(url) == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"

    def test_url_trailing_slash(self) -> None:
        from wos.google_docs import parse_doc_url

        url = "https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/"
        assert parse_doc_url(url) == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"

    def test_url_no_trailing_slash(self) -> None:
        from wos.google_docs import parse_doc_url

        url = "https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ"
        assert parse_doc_url(url) == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"

    def test_raw_document_id(self) -> None:
        from wos.google_docs import parse_doc_url

        assert parse_doc_url("1aBcDeFgHiJkLmNoPqRsTuVwXyZ") == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"

    def test_invalid_url_raises(self) -> None:
        import pytest
        from wos.google_docs import parse_doc_url

        with pytest.raises(ValueError, match="Cannot extract document ID"):
            parse_doc_url("https://example.com/not-a-google-doc")

    def test_url_with_query_params(self) -> None:
        from wos.google_docs import parse_doc_url

        url = "https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit?usp=sharing"
        assert parse_doc_url(url) == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_google_docs.py::TestParseDocUrl -v`
Expected: 7 FAILED (NotImplementedError)

**Step 3: Implement `parse_doc_url`**

Replace the stub in `wos/google_docs.py`:

```python
_DOC_URL_PATTERN = re.compile(
    r"https?://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)"
)

# Google Doc IDs are alphanumeric with hyphens and underscores, typically 25-60 chars
_RAW_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{10,}$")


def parse_doc_url(url_or_id: str) -> str:
    """Extract a Google Docs document ID from a URL or raw ID."""
    match = _DOC_URL_PATTERN.search(url_or_id)
    if match:
        return match.group(1)
    if _RAW_ID_PATTERN.match(url_or_id):
        return url_or_id
    raise ValueError(f"Cannot extract document ID from: {url_or_id}")
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_google_docs.py::TestParseDocUrl -v`
Expected: 7 PASSED

**Step 5: Lint**

Run: `ruff check wos/google_docs.py tests/test_google_docs.py`
Expected: clean

**Step 6: Commit**

```bash
git add wos/google_docs.py tests/test_google_docs.py
git commit -m "feat: add Google Docs URL parser with tests"
```

---

### Task 3: Text extraction — paragraphs and headings

**Files:**
- Create: `tests/fixtures/google_docs_simple.json`
- Modify: `wos/google_docs.py`
- Modify: `tests/test_google_docs.py`

**Step 1: Create a fixture for simple paragraphs + headings**

Create `tests/fixtures/google_docs_simple.json`:

```json
{
  "title": "Test Document",
  "documentId": "test-doc-id",
  "body": {
    "content": [
      {
        "startIndex": 1,
        "endIndex": 1,
        "sectionBreak": {
          "sectionStyle": {
            "columnSeparatorStyle": "NONE",
            "contentDirection": "LEFT_TO_RIGHT"
          }
        }
      },
      {
        "startIndex": 1,
        "endIndex": 16,
        "paragraph": {
          "elements": [
            {
              "startIndex": 1,
              "endIndex": 16,
              "textRun": {
                "content": "Main Heading\n",
                "textStyle": {}
              }
            }
          ],
          "paragraphStyle": {
            "namedStyleType": "HEADING_1",
            "direction": "LEFT_TO_RIGHT"
          }
        }
      },
      {
        "startIndex": 16,
        "endIndex": 50,
        "paragraph": {
          "elements": [
            {
              "startIndex": 16,
              "endIndex": 50,
              "textRun": {
                "content": "This is a simple paragraph.\n",
                "textStyle": {}
              }
            }
          ],
          "paragraphStyle": {
            "namedStyleType": "NORMAL_TEXT",
            "direction": "LEFT_TO_RIGHT"
          }
        }
      },
      {
        "startIndex": 50,
        "endIndex": 70,
        "paragraph": {
          "elements": [
            {
              "startIndex": 50,
              "endIndex": 70,
              "textRun": {
                "content": "Sub Heading\n",
                "textStyle": {}
              }
            }
          ],
          "paragraphStyle": {
            "namedStyleType": "HEADING_2",
            "direction": "LEFT_TO_RIGHT"
          }
        }
      },
      {
        "startIndex": 70,
        "endIndex": 100,
        "paragraph": {
          "elements": [
            {
              "startIndex": 70,
              "endIndex": 100,
              "textRun": {
                "content": "Another paragraph here.\n",
                "textStyle": {}
              }
            }
          ],
          "paragraphStyle": {
            "namedStyleType": "NORMAL_TEXT",
            "direction": "LEFT_TO_RIGHT"
          }
        }
      }
    ]
  }
}
```

**Step 2: Write the failing tests**

Add to `tests/test_google_docs.py`:

```python
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


class TestExtractText:
    def test_simple_paragraphs_and_headings(self) -> None:
        from wos.google_docs import extract_text

        doc = json.loads((FIXTURES / "google_docs_simple.json").read_text())
        result = extract_text(doc)

        assert "# Main Heading" in result
        assert "## Sub Heading" in result
        assert "This is a simple paragraph." in result
        assert "Another paragraph here." in result

    def test_heading_levels(self) -> None:
        from wos.google_docs import extract_text

        doc = {
            "title": "Test",
            "body": {
                "content": [
                    _heading("H1 Title", "HEADING_1"),
                    _heading("H2 Title", "HEADING_2"),
                    _heading("H3 Title", "HEADING_3"),
                ]
            },
        }
        result = extract_text(doc)
        assert "# H1 Title" in result
        assert "## H2 Title" in result
        assert "### H3 Title" in result

    def test_empty_document(self) -> None:
        from wos.google_docs import extract_text

        doc = {"title": "Empty", "body": {"content": []}}
        result = extract_text(doc)
        assert result.strip() == ""


def _heading(text: str, style: str) -> dict:
    """Build a minimal heading structural element."""
    return {
        "paragraph": {
            "elements": [{"textRun": {"content": text + "\n", "textStyle": {}}}],
            "paragraphStyle": {"namedStyleType": style},
        }
    }


def _paragraph(text: str) -> dict:
    """Build a minimal paragraph structural element."""
    return {
        "paragraph": {
            "elements": [{"textRun": {"content": text + "\n", "textStyle": {}}}],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        }
    }
```

**Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_google_docs.py::TestExtractText -v`
Expected: 3 FAILED (NotImplementedError)

**Step 4: Implement basic `extract_text`**

Replace the stub in `wos/google_docs.py`:

```python
_HEADING_MAP = {
    "HEADING_1": "#",
    "HEADING_2": "##",
    "HEADING_3": "###",
    "HEADING_4": "####",
    "HEADING_5": "#####",
    "HEADING_6": "######",
}


def extract_text(doc: Dict[str, Any]) -> str:
    """Convert a Google Docs API response to markdown."""
    body = doc.get("body", {})
    content = body.get("content", [])
    parts: List[str] = []

    for element in content:
        if "paragraph" in element:
            parts.append(_render_paragraph(element["paragraph"]))
        elif "table" in element:
            parts.append(_render_table(element["table"]))

    return "\n".join(parts)


def _render_paragraph(para: Dict[str, Any]) -> str:
    """Render a single paragraph as markdown."""
    style = para.get("paragraphStyle", {})
    named_style = style.get("namedStyleType", "NORMAL_TEXT")
    elements = para.get("elements", [])

    text = ""
    for elem in elements:
        text += _render_element(elem)

    # Strip the trailing newline that Google Docs always includes
    text = text.rstrip("\n")

    if not text:
        return ""

    prefix = _HEADING_MAP.get(named_style, "")
    if prefix:
        return f"{prefix} {text}"
    return text


def _render_element(elem: Dict[str, Any]) -> str:
    """Render a single paragraph element."""
    text_run = elem.get("textRun")
    if not text_run:
        # inlineObjectElement, pageBreak, autoText — skip for now
        return ""
    return text_run.get("content", "")


def _render_table(table: Dict[str, Any]) -> str:
    """Render a table as markdown."""
    # Stub — implemented in Task 6
    return ""
```

**Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_google_docs.py::TestExtractText -v`
Expected: 3 PASSED

**Step 6: Run all tests**

Run: `uv run python -m pytest tests/ -v`
Expected: all pass

**Step 7: Commit**

```bash
git add wos/google_docs.py tests/test_google_docs.py tests/fixtures/google_docs_simple.json
git commit -m "feat: extract paragraphs and headings from Google Docs JSON"
```

---

### Task 4: Text extraction — inline formatting (bold, italic, links)

**Files:**
- Modify: `wos/google_docs.py`
- Modify: `tests/test_google_docs.py`

**Step 1: Write the failing tests**

Add to `TestExtractText` in `tests/test_google_docs.py`:

```python
    def test_bold_text(self) -> None:
        from wos.google_docs import extract_text

        doc = _doc_with_elements([
            {"textRun": {"content": "Hello ", "textStyle": {}}},
            {"textRun": {"content": "world", "textStyle": {"bold": True}}},
            {"textRun": {"content": "!\n", "textStyle": {}}},
        ])
        result = extract_text(doc)
        assert "Hello **world**!" in result

    def test_italic_text(self) -> None:
        from wos.google_docs import extract_text

        doc = _doc_with_elements([
            {"textRun": {"content": "This is ", "textStyle": {}}},
            {"textRun": {"content": "emphasized", "textStyle": {"italic": True}}},
            {"textRun": {"content": " text.\n", "textStyle": {}}},
        ])
        result = extract_text(doc)
        assert "This is *emphasized* text." in result

    def test_bold_italic_text(self) -> None:
        from wos.google_docs import extract_text

        doc = _doc_with_elements([
            {"textRun": {"content": "both", "textStyle": {"bold": True, "italic": True}}},
            {"textRun": {"content": "\n", "textStyle": {}}},
        ])
        result = extract_text(doc)
        assert "***both***" in result

    def test_link(self) -> None:
        from wos.google_docs import extract_text

        doc = _doc_with_elements([
            {"textRun": {"content": "Click ", "textStyle": {}}},
            {"textRun": {
                "content": "here",
                "textStyle": {"link": {"url": "https://example.com"}},
            }},
            {"textRun": {"content": " for more.\n", "textStyle": {}}},
        ])
        result = extract_text(doc)
        assert "Click [here](https://example.com) for more." in result
```

Also add a helper at the bottom of the test file:

```python
def _doc_with_elements(
    elements: list, style: str = "NORMAL_TEXT"
) -> dict:
    """Build a minimal Google Docs JSON with one paragraph."""
    return {
        "title": "Test",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": elements,
                        "paragraphStyle": {"namedStyleType": style},
                    }
                }
            ]
        },
    }
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_google_docs.py -k "bold or italic or link" -v`
Expected: 4 FAILED

**Step 3: Update `_render_element` to handle formatting**

In `wos/google_docs.py`, replace `_render_element`:

```python
def _render_element(elem: Dict[str, Any]) -> str:
    """Render a single paragraph element with markdown formatting."""
    text_run = elem.get("textRun")
    if not text_run:
        inline_obj = elem.get("inlineObjectElement")
        if inline_obj:
            return "[image]"
        return ""

    content = text_run.get("content", "")
    style = text_run.get("textStyle", {})

    # Don't format whitespace-only runs
    stripped = content.strip()
    if not stripped:
        return content

    # Preserve leading/trailing whitespace around formatting
    leading = content[: len(content) - len(content.lstrip())]
    trailing = content[len(content.rstrip()) :]
    inner = content.strip()

    # Apply link
    link = style.get("link", {})
    url = link.get("url")
    if url:
        inner = f"[{inner}]({url})"

    # Apply bold/italic
    bold = style.get("bold", False)
    italic = style.get("italic", False)
    if bold and italic:
        inner = f"***{inner}***"
    elif bold:
        inner = f"**{inner}**"
    elif italic:
        inner = f"*{inner}*"

    return leading + inner + trailing
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_google_docs.py -v`
Expected: all PASSED

**Step 5: Commit**

```bash
git add wos/google_docs.py tests/test_google_docs.py
git commit -m "feat: support bold, italic, and link formatting in extraction"
```

---

### Task 5: Text extraction — bullet and numbered lists

**Files:**
- Modify: `wos/google_docs.py`
- Modify: `tests/test_google_docs.py`

**Step 1: Write the failing tests**

Add to `TestExtractText`:

```python
    def test_bullet_list(self) -> None:
        from wos.google_docs import extract_text

        doc = {
            "title": "Test",
            "body": {
                "content": [
                    _bullet_item("First item", nest_level=0),
                    _bullet_item("Second item", nest_level=0),
                    _bullet_item("Nested item", nest_level=1),
                ]
            },
        }
        result = extract_text(doc)
        assert "- First item" in result
        assert "- Second item" in result
        assert "  - Nested item" in result

    def test_numbered_list(self) -> None:
        from wos.google_docs import extract_text

        doc = {
            "title": "Test",
            "body": {
                "content": [
                    _numbered_item("Step one", nest_level=0),
                    _numbered_item("Step two", nest_level=0),
                ]
            },
        }
        result = extract_text(doc)
        assert "1. Step one" in result
        assert "2. Step two" in result
```

Add helpers:

```python
def _bullet_item(text: str, nest_level: int = 0) -> dict:
    """Build a bullet list item structural element."""
    return {
        "paragraph": {
            "elements": [
                {"textRun": {"content": text + "\n", "textStyle": {}}}
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "bullet": {
                "listId": "kix.list001",
                "nestingLevel": nest_level,
            },
        }
    }


def _numbered_item(text: str, nest_level: int = 0) -> dict:
    """Build a numbered list item structural element."""
    return {
        "paragraph": {
            "elements": [
                {"textRun": {"content": text + "\n", "textStyle": {}}}
            ],
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "bullet": {
                "listId": "kix.list002",
                "nestingLevel": nest_level,
            },
        }
    }
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_google_docs.py -k "bullet or numbered" -v`
Expected: 2 FAILED

**Step 3: Implement list rendering**

In `wos/google_docs.py`, update `extract_text` to track list state, and update `_render_paragraph`:

Add a module-level variable and update the function signatures:

```python
def extract_text(doc: Dict[str, Any]) -> str:
    """Convert a Google Docs API response to markdown."""
    body = doc.get("body", {})
    content = body.get("content", [])
    lists = doc.get("lists", {})
    parts: List[str] = []
    numbered_counters: Dict[str, Dict[int, int]] = {}

    for element in content:
        if "paragraph" in element:
            parts.append(
                _render_paragraph(element["paragraph"], lists, numbered_counters)
            )
        elif "table" in element:
            parts.append(_render_table(element["table"]))

    return "\n".join(parts)


def _render_paragraph(
    para: Dict[str, Any],
    lists: Dict[str, Any],
    numbered_counters: Dict[str, Dict[int, int]],
) -> str:
    """Render a single paragraph as markdown."""
    style = para.get("paragraphStyle", {})
    named_style = style.get("namedStyleType", "NORMAL_TEXT")
    elements = para.get("elements", [])
    bullet = para.get("bullet")

    text = ""
    for elem in elements:
        text += _render_element(elem)

    text = text.rstrip("\n")

    if not text:
        return ""

    # Headings
    prefix = _HEADING_MAP.get(named_style, "")
    if prefix:
        return f"{prefix} {text}"

    # List items
    if bullet:
        list_id = bullet.get("listId", "")
        nest_level = bullet.get("nestingLevel", 0)
        indent = "  " * nest_level

        # Determine bullet vs numbered from the lists metadata
        # If no lists metadata, check if we're tracking this list as numbered
        list_props = lists.get(list_id, {}).get("listProperties", {})
        nesting_levels = list_props.get("nestingLevels", [])

        is_ordered = False
        if nesting_levels and len(nesting_levels) > nest_level:
            glyph_type = nesting_levels[nest_level].get("glyphType", "")
            is_ordered = glyph_type in (
                "DECIMAL", "ALPHA", "ROMAN",
                "UPPER_ALPHA", "UPPER_ROMAN",
            )

        if is_ordered:
            counters = numbered_counters.setdefault(list_id, {})
            counters[nest_level] = counters.get(nest_level, 0) + 1
            num = counters[nest_level]
            return f"{indent}{num}. {text}"
        else:
            return f"{indent}- {text}"

    return text
```

**Note:** Google Docs includes a `lists` top-level key in the response that describes list properties (ordered vs unordered). If this key is absent (as in simplified test fixtures), we default to unordered. The numbered list test fixture should include a `lists` key:

Update the `_numbered_item` helper to also build a doc with a `lists` key, or update the test to include it:

```python
    def test_numbered_list(self) -> None:
        from wos.google_docs import extract_text

        doc = {
            "title": "Test",
            "lists": {
                "kix.list002": {
                    "listProperties": {
                        "nestingLevels": [
                            {"glyphType": "DECIMAL"},
                        ]
                    }
                }
            },
            "body": {
                "content": [
                    _numbered_item("Step one", nest_level=0),
                    _numbered_item("Step two", nest_level=0),
                ]
            },
        }
        result = extract_text(doc)
        assert "1. Step one" in result
        assert "2. Step two" in result
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_google_docs.py -v`
Expected: all PASSED

**Step 5: Commit**

```bash
git add wos/google_docs.py tests/test_google_docs.py
git commit -m "feat: support bullet and numbered lists in extraction"
```

---

### Task 6: Text extraction — tables

**Files:**
- Modify: `wos/google_docs.py`
- Modify: `tests/test_google_docs.py`

**Step 1: Write the failing test**

Add to `TestExtractText`:

```python
    def test_table(self) -> None:
        from wos.google_docs import extract_text

        doc = {
            "title": "Test",
            "body": {
                "content": [
                    {
                        "table": {
                            "rows": 2,
                            "columns": 2,
                            "tableRows": [
                                {
                                    "tableCells": [
                                        {"content": [_paragraph("Name")]},
                                        {"content": [_paragraph("Age")]},
                                    ]
                                },
                                {
                                    "tableCells": [
                                        {"content": [_paragraph("Alice")]},
                                        {"content": [_paragraph("30")]},
                                    ]
                                },
                            ],
                        }
                    }
                ]
            },
        }
        result = extract_text(doc)
        assert "| Name | Age |" in result
        assert "| --- | --- |" in result
        assert "| Alice | 30 |" in result
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_google_docs.py::TestExtractText::test_table -v`
Expected: FAILED (empty string from stub)

**Step 3: Implement `_render_table`**

In `wos/google_docs.py`, replace the `_render_table` stub:

```python
def _render_table(table: Dict[str, Any]) -> str:
    """Render a table as a markdown table."""
    rows = table.get("tableRows", [])
    if not rows:
        return ""

    rendered_rows: List[List[str]] = []
    for row in rows:
        cells = row.get("tableCells", [])
        rendered_cells: List[str] = []
        for cell in cells:
            cell_content = cell.get("content", [])
            cell_text = ""
            for element in cell_content:
                if "paragraph" in element:
                    para = element["paragraph"]
                    for elem in para.get("elements", []):
                        cell_text += _render_element(elem)
            # Clean up: strip newlines, collapse whitespace
            cell_text = cell_text.strip().replace("\n", " ")
            rendered_cells.append(cell_text)
        rendered_rows.append(rendered_cells)

    if not rendered_rows:
        return ""

    # Build markdown table
    lines: List[str] = []
    # Header row
    header = rendered_rows[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    # Data rows
    for row in rendered_rows[1:]:
        # Pad row to match header length if needed
        while len(row) < len(header):
            row.append("")
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_google_docs.py -v`
Expected: all PASSED

**Step 5: Commit**

```bash
git add wos/google_docs.py tests/test_google_docs.py
git commit -m "feat: support table extraction as markdown tables"
```

---

### Task 7: Auth subcommand

**Files:**
- Modify: `scripts/google_docs.py`

This task implements the OAuth flow. It cannot be unit tested without real Google credentials, so we test it manually and add integration test scaffolding in Task 9.

**Step 1: Implement `_load_credentials` and `_save_credentials` helpers**

Add to `scripts/google_docs.py` after the constants:

```python
def _load_credentials():
    """Load existing Google OAuth credentials from disk.

    Returns:
        Credentials object or None if not found / invalid.
    """
    from google.oauth2.credentials import Credentials

    if not TOKEN_PATH.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    except (ValueError, KeyError):
        return None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request

        try:
            creds.refresh(Request())
            _save_credentials(creds)
            return creds
        except Exception:
            return None

    return None


def _save_credentials(creds) -> None:
    """Persist credentials to disk with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    TOKEN_PATH.chmod(0o600)
```

**Step 2: Implement `cmd_auth`**

Replace the `cmd_auth` stub:

```python
def cmd_auth(args: argparse.Namespace) -> None:
    """Authenticate with Google and store credentials."""
    # --check: silent auth verification
    if args.check:
        creds = _load_credentials()
        sys.exit(0 if creds else 1)

    # If not --force, check for existing valid creds
    if not args.force:
        creds = _load_credentials()
        if creds:
            print("Already authenticated. Use --force to re-authenticate.")
            sys.exit(0)

    # Locate client secret
    client_secret = Path(args.client_secret) if args.client_secret else CLIENT_SECRET_PATH
    if not client_secret.exists():
        print(
            f"Client secret not found at {client_secret}\n\n"
            "To set up Google Docs access:\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a project and enable the Google Docs API and Google Drive API\n"
            "3. Create OAuth 2.0 credentials (Desktop app type)\n"
            "4. Download the JSON and save it to:\n"
            f"   {CLIENT_SECRET_PATH}\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)

    # Try browser-based flow, fall back to console
    try:
        creds = flow.run_local_server(port=0)
    except Exception:
        print("Browser auth unavailable, using manual flow.", file=sys.stderr)
        creds = flow.run_console()

    _save_credentials(creds)
    print(f"Authenticated successfully. Token saved to {TOKEN_PATH}")
```

**Step 3: Verify script parses correctly**

Run: `uv run scripts/google_docs.py auth --help`
Expected: shows help text (does not import google libs at parse time)

**Step 4: Commit**

```bash
git add scripts/google_docs.py
git commit -m "feat: implement Google OAuth auth subcommand"
```

---

### Task 8: Read subcommand

**Files:**
- Modify: `scripts/google_docs.py`

**Step 1: Implement `cmd_read`**

Replace the `cmd_read` stub:

```python
def cmd_read(args: argparse.Namespace) -> None:
    """Read a Google Doc and output as markdown."""
    from wos.google_docs import extract_text, parse_doc_url

    creds = _load_credentials()
    if not creds:
        print(
            "Not authenticated. Run: uv run scripts/google_docs.py auth",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        doc_id = parse_doc_url(args.url)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    from googleapiclient.discovery import build

    service = build("docs", "v1", credentials=creds)
    doc = service.documents().get(documentId=doc_id).execute()

    if args.json_output:
        print(json.dumps(doc, indent=2))
    else:
        print(extract_text(doc))
```

**Step 2: Verify script parses correctly**

Run: `uv run scripts/google_docs.py read --help`
Expected: shows help text

**Step 3: Commit**

```bash
git add scripts/google_docs.py
git commit -m "feat: implement read subcommand for Google Docs"
```

---

### Task 9: List subcommand

**Files:**
- Modify: `scripts/google_docs.py`

**Step 1: Implement `cmd_list`**

Replace the `cmd_list` stub:

```python
def cmd_list(args: argparse.Namespace) -> None:
    """List recent Google Docs."""
    creds = _load_credentials()
    if not creds:
        print(
            "Not authenticated. Run: uv run scripts/google_docs.py auth",
            file=sys.stderr,
        )
        sys.exit(1)

    from googleapiclient.discovery import build

    service = build("drive", "v3", credentials=creds)

    query = "mimeType='application/vnd.google-apps.document' and trashed=false"
    if args.query:
        query += f" and name contains '{args.query}'"

    results = (
        service.files()
        .list(
            q=query,
            pageSize=args.limit,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )

    files = results.get("files", [])
    if not files:
        print("No documents found.")
        return

    # Header
    print(f"{'title':<50} | {'modified':<12} | url")
    print("-" * 50 + "-+-" + "-" * 12 + "-+-" + "-" * 50)

    for f in files:
        title = f["name"][:50]
        modified = f.get("modifiedTime", "")[:10]
        url = f"https://docs.google.com/document/d/{f['id']}/edit"
        print(f"{title:<50} | {modified:<12} | {url}")
```

**Step 2: Verify script parses correctly**

Run: `uv run scripts/google_docs.py list --help`
Expected: shows help text

**Step 3: Commit**

```bash
git add scripts/google_docs.py
git commit -m "feat: implement list subcommand for Google Docs"
```

---

### Task 10: `/wos:read` skill definition

**Files:**
- Create: `skills/read/SKILL.md`

**Step 1: Create the skill directory and file**

```bash
mkdir -p skills/read
```

**Step 2: Write the skill definition**

Create `skills/read/SKILL.md`:

```markdown
---
name: read
description: Read external documents (Google Docs) for live reference or ingestion into WOS context
user-invocable: true
argument-hint: "[Google Doc URL or search terms]"
---

# Read External Documents

Read content from external document platforms. Currently supports Google Docs.

## Routing

Detect intent from the user's request:

| Intent | Action |
|--------|--------|
| User provides a Google Doc URL | Read that specific document |
| User describes a document by name | Search with `list`, then read |
| User wants to reference content in conversation | Live read — display content |
| User wants to save content as WOS context | Ingest — create context file via `/wos:create` |

## Preflight

Before any operation, verify the environment:

1. Check `uv` is available: `which uv`
2. If the user has never authenticated, guide them through setup:
   - They need a Google Cloud project with Docs API and Drive API enabled
   - They need OAuth 2.0 credentials (Desktop app type)
   - Client secret saved to `~/.config/wos/google-client-secret.json`
   - Run: `uv run scripts/google_docs.py auth`

## Reading a Document

When the user provides a URL or you've identified the document:

```bash
uv run scripts/google_docs.py read "<url>"
```

This outputs the document content as markdown to stdout.

For raw JSON (rarely needed):
```bash
uv run scripts/google_docs.py read "<url>" --json
```

## Finding a Document

When the user describes a document but doesn't have the URL:

```bash
uv run scripts/google_docs.py list --query "search terms" --limit 10
```

Present the results and let the user pick which document to read.

## Ingestion Mode

When the user wants to save the content as a WOS context file:

1. Read the document as above
2. Note the word count — context files should target 200-800 words
3. If the content exceeds 800 words, suggest splitting into multiple files
4. Use `/wos:create` to create the context file, with:
   - The Google Doc URL in `sources:` frontmatter
   - Appropriate `related:` links to other context files
   - Content adapted for the context format (may need summarization)

## Auth Check

To silently verify auth status:

```bash
uv run scripts/google_docs.py auth --check
```

Exit code 0 = authenticated, 1 = not authenticated.

## Troubleshooting

| Error | Solution |
|-------|----------|
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `Client secret not found` | Download OAuth credentials from Google Cloud Console |
| `Token expired` | Run `uv run scripts/google_docs.py auth --force` |
| `ModuleNotFoundError` | Ensure you're using `uv run`, not `python3` directly |
```

**Step 3: Commit**

```bash
git add skills/read/SKILL.md
git commit -m "feat: add /wos:read skill for Google Docs integration"
```

---

### Task 11: Integration test scaffolding

**Files:**
- Modify: `tests/test_google_docs.py`
- Modify: `pyproject.toml`

**Step 1: Add integration marker to pyproject.toml**

Add to `[tool.pytest.ini_options]` in `pyproject.toml`:

```toml
markers = [
    "integration: tests requiring real Google credentials (deselect with '-m not integration')",
]
```

**Step 2: Add integration tests**

Add to `tests/test_google_docs.py`:

```python
import pytest


@pytest.mark.integration
class TestGoogleDocsIntegration:
    """Integration tests — require real Google credentials.

    Run with: uv run python -m pytest tests/test_google_docs.py -m integration -v

    Prerequisites:
    - Google Cloud project with Docs API enabled
    - OAuth credentials at ~/.config/wos/google-client-secret.json
    - Authenticated via: uv run scripts/google_docs.py auth
    """

    def test_auth_check(self) -> None:
        """Verify auth --check returns 0 when authenticated."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "scripts/google_docs.py", "auth", "--check"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Not authenticated — run auth first"

    def test_read_public_doc(self) -> None:
        """Read a known Google Doc and verify markdown output."""
        import subprocess

        # Use a publicly accessible Google Doc for testing
        # Replace with a stable test document URL
        result = subprocess.run(
            ["uv", "run", "scripts/google_docs.py", "read",
             "https://docs.google.com/document/d/1BxiMkUfp2WVXE5mYf3CScJVZ9V55M5z3rjq3RZwmpI/edit"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"read failed: {result.stderr}"
        assert len(result.stdout) > 0, "No content returned"

    def test_list_docs(self) -> None:
        """List documents and verify table output."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "scripts/google_docs.py", "list", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"list failed: {result.stderr}"
```

**Step 3: Verify integration tests are skipped by default**

Run: `uv run python -m pytest tests/test_google_docs.py -v`
Expected: integration tests show as SKIPPED (if using `-m "not integration"` default) or simply not selected

Run: `uv run python -m pytest tests/ -v`
Expected: all unit tests pass, integration tests collected but not skipped unless explicitly deselected

**Step 4: Commit**

```bash
git add tests/test_google_docs.py pyproject.toml
git commit -m "feat: add integration test scaffolding for Google Docs"
```

---

### Task 12: Final verification and cleanup

**Files:**
- Modify: `docs/plans/2026-02-26-google-docs-read-plan.md` (check off tasks)

**Step 1: Run full test suite**

Run: `uv run python -m pytest tests/ -v`
Expected: all tests pass

**Step 2: Run linter**

Run: `ruff check wos/ scripts/ tests/`
Expected: clean (or fix any issues)

**Step 3: Verify script help**

Run: `uv run scripts/google_docs.py --help`
Run: `uv run scripts/google_docs.py auth --help`
Run: `uv run scripts/google_docs.py read --help`
Run: `uv run scripts/google_docs.py list --help`
Expected: all show correct help text

**Step 4: Update plan with completion status**

Mark all tasks complete in this plan file.

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup for Google Docs read integration"
```

**Step 6: Create pull request**

```bash
git push -u origin feat/google-docs-read
gh pr create --title "feat: Google Docs read integration (#41)" --body "..."
```
