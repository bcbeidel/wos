---
name: Research Skill Fixes Implementation Plan
description: Step-by-step plan for fixing GitHub issues #52-55 (research skill)
type: plan
related:
  - docs/plans/2026-02-25-research-skill-fixes-design.md
---

# Research Skill Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the research skill's format mismatch bug, improve DX with a new validate script and reference docs, update the quality gate, and add practical workflow guidance.

**Architecture:** Four independent fix areas that all touch `skills/research/references/research-workflow.md`. Code changes are limited to input validation in `wos/research_protocol.py` and a new `scripts/validate.py`. No existing API signatures change.

**Tech Stack:** Python 3.9, pytest, argparse, existing `wos` package

**Branch:** `fix/research-skill-issues-52-55`
**PR:** TBD

---

### Task 1: Create branch

**Step 1: Create and switch to feature branch**

Run: `git checkout -b fix/research-skill-issues-52-55`

**Step 2: Verify branch**

Run: `git branch --show-current`
Expected: `fix/research-skill-issues-52-55`

---

### Task 2: Add input validation to `_protocol_from_json()` (Issue #52 — code fix)

**Files:**
- Modify: `wos/research_protocol.py:76-91`
- Test: `tests/test_research_protocol.py`

**Step 1: Write the failing test**

Add to `tests/test_research_protocol.py`, inside `class TestProtocolFromJson`:

```python
def test_rejects_dict_not_searched_entries(self) -> None:
    """Issue #52: not_searched with dict entries should raise ValueError."""
    from wos.research_protocol import _protocol_from_json

    data = {
        "entries": [],
        "not_searched": [
            {"source": "Google Scholar", "reason": "covered elsewhere"}
        ],
    }
    try:
        _protocol_from_json(data)
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "not_searched" in str(exc)
        assert "string" in str(exc).lower()

def test_rejects_mixed_not_searched_entries(self) -> None:
    """Issue #52: mix of strings and dicts should also raise."""
    from wos.research_protocol import _protocol_from_json

    data = {
        "entries": [],
        "not_searched": [
            "Reddit - not relevant",
            {"source": "Scholar", "reason": "no access"},
        ],
    }
    try:
        _protocol_from_json(data)
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "not_searched" in str(exc)
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_research_protocol.py::TestProtocolFromJson::test_rejects_dict_not_searched_entries tests/test_research_protocol.py::TestProtocolFromJson::test_rejects_mixed_not_searched_entries -v`
Expected: FAIL (no ValueError raised)

**Step 3: Write minimal implementation**

In `wos/research_protocol.py`, replace the `_protocol_from_json` function (lines 76-91) with:

```python
def _protocol_from_json(data: Dict[str, Any]) -> SearchProtocol:
    """Parse JSON dict into SearchProtocol.

    Raises ValueError if not_searched contains non-string entries.
    """
    entries = [
        SearchEntry(
            query=e["query"],
            source=e["source"],
            date_range=e.get("date_range"),
            results_found=e["results_found"],
            results_used=e["results_used"],
        )
        for e in data.get("entries", [])
    ]
    not_searched = data.get("not_searched", [])
    for item in not_searched:
        if not isinstance(item, str):
            raise ValueError(
                f"not_searched entries must be strings, got {type(item).__name__}. "
                "Use format: 'Source — reason'"
            )
    return SearchProtocol(entries=entries, not_searched=not_searched)
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_research_protocol.py -v`
Expected: ALL PASS (new tests + existing tests)

**Step 5: Commit**

```bash
git add wos/research_protocol.py tests/test_research_protocol.py
git commit -m "fix: validate not_searched entries are strings in _protocol_from_json (#52)"
```

---

### Task 3: Create `scripts/validate.py` (Issue #53 — new CLI)

**Files:**
- Create: `scripts/validate.py`
- Test: `tests/test_validate.py` (new)

**Step 1: Write the failing test**

Create `tests/test_validate.py`:

```python
"""Tests for scripts/validate.py — single-file validation CLI."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch


def _run_validate(*args: str) -> tuple[str, int]:
    """Run validate.main() with the given CLI args, returning (stdout, exitcode)."""
    captured = StringIO()
    exit_code = 0

    with patch.object(sys, "argv", ["validate.py", *args]):
        with patch("sys.stdout", captured):
            try:
                from scripts.validate import main
                main()
            except SystemExit as exc:
                exit_code = exc.code if exc.code is not None else 0

    return captured.getvalue(), exit_code


class TestValidateClean:
    def test_valid_document_passes(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text(
            "---\nname: Test\ndescription: A test doc\n---\nBody\n"
        )
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        assert code == 0
        assert "All checks passed" in stdout

    def test_missing_frontmatter_fails(self, tmp_path: Path) -> None:
        doc = tmp_path / "bad.md"
        doc.write_text("---\nname: Test\n---\nNo description\n")
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        assert code == 1
        assert "FAIL" in stdout

    def test_research_without_sources_fails(self, tmp_path: Path) -> None:
        doc = tmp_path / "research.md"
        doc.write_text(
            "---\nname: Test\ndescription: A test\ntype: research\n---\nBody\n"
        )
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        assert code == 1
        assert "sources" in stdout.lower()

    def test_nonexistent_file_fails(self, tmp_path: Path) -> None:
        stdout, code = _run_validate(
            str(tmp_path / "missing.md"), "--root", str(tmp_path), "--no-urls"
        )
        assert code == 1

    def test_relative_paths_in_output(self, tmp_path: Path) -> None:
        doc = tmp_path / "bad.md"
        doc.write_text("---\nname: Test\n---\nNo description\n")
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        # Should not contain absolute path
        assert str(tmp_path) not in stdout
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validate.py -v`
Expected: FAIL (ModuleNotFoundError — scripts/validate.py doesn't exist)

**Step 3: Write minimal implementation**

Create `scripts/validate.py`:

```python
#!/usr/bin/env python3
"""Validate a single WOS document.

Usage:
    python3 scripts/validate.py <file> [--root DIR] [--no-urls]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _relative_path(file_path: str, root: Path) -> str:
    """Return file_path relative to root, falling back to the original."""
    try:
        return str(Path(file_path).relative_to(root))
    except ValueError:
        return file_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a single WOS document.",
    )
    parser.add_argument(
        "file",
        help="Path to the .md file to validate",
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
    args = parser.parse_args()

    # Deferred imports — keeps --help fast
    from wos.validators import validate_file

    root = Path(args.root).resolve()
    file_path = Path(args.file).resolve()
    issues = validate_file(file_path, root, verify_urls=not args.no_urls)

    if issues:
        for issue in issues:
            rel = _relative_path(issue["file"], root)
            print(f"[FAIL] {rel}: {issue['issue']}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_validate.py -v`
Expected: ALL PASS

**Step 5: Run full test suite for regressions**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add scripts/validate.py tests/test_validate.py
git commit -m "feat: add scripts/validate.py for single-file validation (#53)"
```

---

### Task 4: Create `python-utilities.md` reference doc (Issue #53 — docs)

**Files:**
- Create: `skills/research/references/python-utilities.md`

**Step 1: Create the reference document**

Create `skills/research/references/python-utilities.md`:

```markdown
# Python Utilities Reference

CLI commands available during research sessions. All scripts are run from
the project root.

## Validate a Single Document

Runs all 4 checks: frontmatter, research sources, source URLs, related paths.

```bash
python3 scripts/validate.py <file> [--root DIR] [--no-urls]
```

Example:
```bash
python3 scripts/validate.py docs/research/2026-02-25-my-research.md --no-urls
```

Output on success:
```
All checks passed.
```

Output on failure:
```
[FAIL] docs/research/my-research.md: Research document has no sources
```

## Validate Entire Project

Runs all 5 checks across `context/` and `artifacts/`.

```bash
python3 scripts/audit.py [--root DIR] [--no-urls] [--json] [--fix]
```

## Format Search Protocol

Renders a search protocol JSON as a markdown table.

```bash
echo '<json>' | python3 -m wos.research_protocol format
echo '<json>' | python3 -m wos.research_protocol format --summary
```

### Search Protocol JSON Schema

```json
{
  "entries": [
    {
      "query": "search terms used",
      "source": "google",
      "date_range": "2024-2026 or null",
      "results_found": 12,
      "results_used": 3
    }
  ],
  "not_searched": [
    "Google Scholar - covered by direct source fetching",
    "PubMed - topic is not biomedical"
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `entries[].query` | string | Search terms used |
| `entries[].source` | string | Search engine (e.g., `google`, `scholar`, `github`, `docs`) |
| `entries[].date_range` | string or null | Date filter applied (e.g., `"2024-2026"`) |
| `entries[].results_found` | int | Total results returned |
| `entries[].results_used` | int | Results kept for evaluation |
| `not_searched` | list of strings | Sources not searched, with reason (e.g., `"Reddit - not relevant to topic"`) |

### Example Output (table)

```
| Query | Source | Date Range | Found | Used |
|-------|--------|------------|-------|------|
| python asyncio patterns | google | 2024-2026 | 12 | 3 |
| asyncio best practices | google | — | 8 | 2 |

**Not searched:** Google Scholar - covered by direct source fetching
```

### Example Output (summary)

```
2 searches across 1 source, 20 results found, 5 used
```

## Document Model

The `Document` dataclass fields relevant to research:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Concise title |
| `description` | string | Yes | One-sentence summary |
| `type` | string | No | Set to `research` for research docs |
| `sources` | list of strings | For research | URLs of verified sources |
| `related` | list of strings | No | Relative paths to related documents |
```

**Step 2: Commit**

```bash
git add skills/research/references/python-utilities.md
git commit -m "docs: add python utilities reference for research workflow (#53)"
```

---

### Task 5: Update `research-workflow.md` — fix `not_searched` examples (Issue #52 — docs)

**Files:**
- Modify: `skills/research/references/research-workflow.md:42-43`

**Step 1: Update the `not_searched` guidance in Phase 2**

In `skills/research/references/research-workflow.md`, replace lines 42-43:

Old:
```
7. After gathering is complete, record sources you considered but did
   not search in `not_searched` with a brief reason
```

New:
```
7. After gathering is complete, record sources you considered but did
   not search in `not_searched` as strings with a brief reason:

```json
"not_searched": [
  "Google Scholar - covered by direct source fetching",
  "PubMed - topic is not biomedical"
]
```
```

**Step 2: Run tests (sanity check — no code changed)**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add skills/research/references/research-workflow.md
git commit -m "docs: clarify not_searched format as List[str] with examples (#52)"
```

---

### Task 6: Update quality gate in `research-workflow.md` (Issue #54 — docs)

**Files:**
- Modify: `skills/research/references/research-workflow.md:170`

**Step 1: Update the quality checklist**

In `skills/research/references/research-workflow.md`, replace line 170:

Old:
```
- [ ] Document passes `parse_document()` validation
```

New:
```
- [ ] Document passes validation: `python3 scripts/validate.py <file> --no-urls`
```

**Step 2: Commit**

```bash
git add skills/research/references/research-workflow.md
git commit -m "docs: update quality gate to use scripts/validate.py (#54)"
```

---

### Task 7: Add fetch failure guidance to workflow (Issue #55 — docs)

**Files:**
- Modify: `skills/research/references/research-workflow.md` (Phase 2 section)

**Step 1: Add fetch failure callout after Phase 2, step 7**

In `skills/research/references/research-workflow.md`, after the `not_searched` guidance added in Task 5 (end of Phase 2), add:

```markdown

> **Handling fetch failures:** When parallel `WebFetch` calls fail, a single
> failure can cascade to sibling calls ("Sibling tool call errored"). Retry
> failed URLs individually. Common failure modes:
> - **403** — bot protection; source exists but can't be fetched. Retain if
>   from a published venue.
> - **303/301** — redirect; retry with the redirect URL.
> - **Timeout** — retry once, then skip. Do not drop sources solely because
>   fetching failed — assess based on URL verification status.
```

**Step 2: Commit**

```bash
git add skills/research/references/research-workflow.md
git commit -m "docs: add fetch failure guidance to research workflow (#55)"
```

---

### Task 8: Add source diversity guidance to workflow (Issue #55 — docs)

**Files:**
- Modify: `skills/research/references/research-workflow.md` (Phase 1 section)

**Step 1: Add source diversity callout at end of Phase 1**

In `skills/research/references/research-workflow.md`, after the protocol initialization JSON in Phase 1 (after line 21), add:

```markdown

> **Source diversity:** `WebSearch` routes through a single search engine. To
> improve source diversity: (1) vary query terms to surface different source
> types, (2) fetch known database URLs directly (e.g., PubMed, Semantic
> Scholar) when relevant, (3) log `"google"` as the source honestly — this is
> expected. The `not_searched` field should list sources you chose not to
> search, not sources the tool can't access.
```

**Step 2: Commit**

```bash
git add skills/research/references/research-workflow.md
git commit -m "docs: add source diversity guidance to research workflow (#55)"
```

---

### Task 9: Final verification and cleanup

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 2: Run linter (if available)**

Run: `ruff check wos/ tests/ scripts/`
Expected: No errors (or note if ruff is not installed locally)

**Step 3: Review all changes**

Run: `git log --oneline main..HEAD`
Expected: 7 commits (one per task 2-8)

Run: `git diff main --stat`
Expected: Changes in:
- `wos/research_protocol.py` (validation added)
- `tests/test_research_protocol.py` (new tests)
- `scripts/validate.py` (new file)
- `tests/test_validate.py` (new file)
- `skills/research/references/python-utilities.md` (new file)
- `skills/research/references/research-workflow.md` (multiple updates)

**Step 4: Mark plan checkboxes complete**

Update this plan file, checking off all completed tasks.
