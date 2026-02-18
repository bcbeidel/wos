# Token Budget Estimation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add token budget estimation to `/wos:health` output so users can see the aggregate token cost of their context files.

**Architecture:** New module `wos/token_budget.py` with one public function that takes parsed `Document` objects, estimates tokens via `words × 1.3`, groups by area, and returns a budget dict with optional warn issue. The health script filters to `context/` docs, calls the function, and merges the result into the JSON output.

**Tech Stack:** Python 3.9, Pydantic (existing), pytest

**Design doc:** `docs/plans/2026-02-18-token-budget-design.md`

---

### Task 1: Core estimation function — failing tests

**Files:**
- Create: `tests/test_token_budget.py`
- Create: `wos/token_budget.py`

**Step 1: Write the failing tests**

Create `tests/test_token_budget.py`:

```python
"""Tests for wos.token_budget — token budget estimation.

All tests use inline markdown strings.
"""

from __future__ import annotations

from wos.document_types import parse_document
from wos.token_budget import estimate_token_budget


# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(word_count: int = 50) -> str:
    """Build a minimal topic with approximately word_count words of content."""
    words = " ".join(["word"] * word_count)
    return (
        "---\n"
        "document_type: topic\n"
        'description: "A test topic document"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Test Topic\n"
        "\n"
        "## Guidance\n\n"
        f"{words}\n\n"
        "## Context\n\nBackground.\n\n"
        "## In Practice\n\nExample.\n\n"
        "## Pitfalls\n\nAvoid this.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )


def _overview_md(word_count: int = 40) -> str:
    """Build a minimal overview with approximately word_count words."""
    words = " ".join(["word"] * word_count)
    return (
        "---\n"
        "document_type: overview\n"
        'description: "Overview of test area"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Test Area\n"
        "\n"
        "## What This Covers\n\n"
        f"{words}\n\n"
        "## Topics\n\n- test-topic\n\n"
        "## Key Sources\n\n- [Source](https://example.com)\n"
    )


# ── Tests ────────────────────────────────────────────────────────


class TestEstimateTokens:
    """Test the word-count-based token estimation."""

    def test_basic_estimation(self):
        """Token estimate equals round(word_count * 1.3)."""
        doc = parse_document("context/python/error-handling.md", _topic_md(100))
        result = estimate_token_budget([doc])
        word_count = len(doc.raw_content.split())
        expected_tokens = round(word_count * 1.3)
        assert result["total_estimated_tokens"] == expected_tokens

    def test_empty_input(self):
        """No documents yields zero tokens and empty areas."""
        result = estimate_token_budget([])
        assert result["total_estimated_tokens"] == 0
        assert result["over_budget"] is False
        assert result["areas"] == []


class TestAreaGrouping:
    """Test per-area aggregation."""

    def test_multiple_areas(self):
        """Documents are grouped by area extracted from path."""
        doc_a = parse_document("context/python/topic-a.md", _topic_md(50))
        doc_b = parse_document("context/python/topic-b.md", _topic_md(50))
        doc_c = parse_document("context/git/topic-c.md", _topic_md(50))

        result = estimate_token_budget([doc_a, doc_b, doc_c])
        areas = {a["area"]: a for a in result["areas"]}

        assert "python" in areas
        assert "git" in areas
        assert areas["python"]["files"] == 2
        assert areas["git"]["files"] == 1

    def test_area_tokens_sum_to_total(self):
        """Per-area token sums equal the total."""
        doc_a = parse_document("context/python/topic-a.md", _topic_md(80))
        doc_b = parse_document("context/git/topic-b.md", _topic_md(60))

        result = estimate_token_budget([doc_a, doc_b])
        area_sum = sum(a["estimated_tokens"] for a in result["areas"])
        assert area_sum == result["total_estimated_tokens"]


class TestThreshold:
    """Test over-budget detection and issue generation."""

    def test_under_threshold(self):
        """Below threshold: over_budget is False, no issue returned."""
        doc = parse_document("context/python/small.md", _topic_md(10))
        result = estimate_token_budget([doc], warning_threshold=40_000)
        assert result["over_budget"] is False
        assert result.get("issue") is None

    def test_over_threshold(self):
        """Above threshold: over_budget is True, warn issue returned."""
        doc = parse_document("context/python/big.md", _topic_md(10))
        # Use a tiny threshold to trigger over-budget
        result = estimate_token_budget([doc], warning_threshold=1)
        assert result["over_budget"] is True
        issue = result["issue"]
        assert issue["severity"] == "warn"
        assert issue["validator"] == "token_budget"
        assert "threshold" in issue["issue"].lower()

    def test_custom_threshold(self):
        """Custom threshold value is used and reported."""
        doc = parse_document("context/python/topic.md", _topic_md(10))
        result = estimate_token_budget([doc], warning_threshold=99_999)
        assert result["warning_threshold"] == 99_999

    def test_exactly_at_threshold(self):
        """At exactly the threshold: not over budget."""
        doc = parse_document("context/python/topic.md", _topic_md(10))
        total = round(len(doc.raw_content.split()) * 1.3)
        result = estimate_token_budget([doc], warning_threshold=total)
        assert result["over_budget"] is False

    def test_areas_sorted_by_name(self):
        """Areas in output are sorted alphabetically."""
        doc_z = parse_document("context/zsh/topic.md", _topic_md(10))
        doc_a = parse_document("context/aws/topic.md", _topic_md(10))

        result = estimate_token_budget([doc_z, doc_a])
        area_names = [a["area"] for a in result["areas"]]
        assert area_names == sorted(area_names)
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_token_budget.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wos.token_budget'`

**Step 3: Commit the failing tests**

```bash
git add tests/test_token_budget.py
git commit -m "test: add failing tests for token budget estimation"
```

---

### Task 2: Core estimation function — implementation

**Files:**
- Create: `wos/token_budget.py`

**Step 1: Implement `estimate_token_budget`**

```python
"""Token budget estimation for context files.

Estimates the aggregate token cost of context documents using a
word-count heuristic (words × 1.3). No tokenizer dependency.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

from wos.document_types import Document

_TOKEN_MULTIPLIER = 1.3
_DEFAULT_WARNING_THRESHOLD = 40_000


def estimate_token_budget(
    documents: List[Document],
    warning_threshold: int = _DEFAULT_WARNING_THRESHOLD,
) -> Dict[str, Any]:
    """Estimate token budget for a set of context documents.

    Args:
        documents: Parsed Document objects (caller should filter to context/ only).
        warning_threshold: Token count above which over_budget is True.

    Returns:
        Dict with total_estimated_tokens, warning_threshold, over_budget,
        areas list, and optionally an issue dict if over budget.
    """
    area_totals: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"files": 0, "estimated_tokens": 0}
    )

    for doc in documents:
        area = _extract_area(doc.path)
        word_count = len(doc.raw_content.split())
        tokens = round(word_count * _TOKEN_MULTIPLIER)
        area_totals[area]["files"] += 1
        area_totals[area]["estimated_tokens"] += tokens

    total_tokens = sum(a["estimated_tokens"] for a in area_totals.values())
    over_budget = total_tokens > warning_threshold

    areas = sorted(
        [{"area": name, **data} for name, data in area_totals.items()],
        key=lambda a: a["area"],
    )

    result: Dict[str, Any] = {
        "total_estimated_tokens": total_tokens,
        "warning_threshold": warning_threshold,
        "over_budget": over_budget,
        "areas": areas,
    }

    if over_budget:
        result["issue"] = {
            "file": "context/",
            "issue": (
                f"Total context estimated at ~{total_tokens:,} tokens "
                f"(threshold: {warning_threshold:,}). "
                "Consider reducing content or splitting areas."
            ),
            "severity": "warn",
            "validator": "token_budget",
            "section": None,
            "suggestion": "Review per-area token counts to identify optimization targets.",
        }

    return result


def _extract_area(path: str) -> str:
    """Extract area name from a context path like 'context/{area}/file.md'."""
    match = re.match(r"context/([^/]+)/", path)
    return match.group(1) if match else "unknown"
```

**Step 2: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_token_budget.py -v`
Expected: All PASS

**Step 3: Run full test suite to verify no regressions**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 4: Run linter**

Run: `ruff check wos/token_budget.py tests/test_token_budget.py`
Expected: No issues

**Step 5: Commit**

```bash
git add wos/token_budget.py tests/test_token_budget.py
git commit -m "feat: add token budget estimation module"
```

---

### Task 3: Health script integration — failing test

**Files:**
- Create: `tests/test_check_health_integration.py`

**Step 1: Write the failing integration test**

This test runs the health script as a subprocess against a temporary project with context files and verifies the JSON output contains a `token_budget` key.

```python
"""Integration test for token_budget in health script output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _write_topic(area_dir: Path, name: str, word_count: int = 50) -> None:
    """Write a minimal valid topic file."""
    words = " ".join(["word"] * word_count)
    content = (
        "---\n"
        "document_type: topic\n"
        f'description: "A topic about {name}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        f"\n# {name.replace('-', ' ').title()}\n\n"
        f"## Guidance\n\n{words}\n\n"
        "## Context\n\nBackground.\n\n"
        "## In Practice\n\nExample.\n\n"
        "## Pitfalls\n\nAvoid this.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )
    (area_dir / f"{name}.md").write_text(content, encoding="utf-8")


def _write_overview(area_dir: Path, area_name: str, topics: list[str]) -> None:
    """Write a minimal valid overview file."""
    topic_list = "\n".join(f"- [{t}]({t}.md)" for t in topics)
    content = (
        "---\n"
        "document_type: overview\n"
        f'description: "Overview of {area_name}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        f"\n# {area_name.replace('-', ' ').title()}\n\n"
        "## What This Covers\n\n"
        "This area covers important concepts that every developer "
        "should understand when working with this technology stack "
        "in production environments.\n\n"
        f"## Topics\n\n{topic_list}\n\n"
        "## Key Sources\n\n- [Source](https://example.com)\n"
    )
    (area_dir / "_overview.md").write_text(content, encoding="utf-8")


class TestHealthScriptTokenBudget:
    """Verify token_budget appears in health script JSON output."""

    def test_token_budget_in_output(self, tmp_path: Path):
        """Health script output includes token_budget dict."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = subprocess.run(
            [sys.executable, "scripts/check_health.py", "--root", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        report = json.loads(result.stdout)

        assert "token_budget" in report
        budget = report["token_budget"]
        assert "total_estimated_tokens" in budget
        assert "warning_threshold" in budget
        assert "over_budget" in budget
        assert "areas" in budget
        assert isinstance(budget["areas"], list)
        assert budget["areas"][0]["area"] == "python"

    def test_token_budget_only_context_files(self, tmp_path: Path):
        """Artifact files are excluded from token budget."""
        # Create context file
        ctx = tmp_path / "context" / "python"
        ctx.mkdir(parents=True)
        _write_topic(ctx, "error-handling")
        _write_overview(ctx, "python", ["error-handling"])

        # Create artifact file (should NOT appear in budget)
        art = tmp_path / "artifacts" / "research"
        art.mkdir(parents=True)
        research_content = (
            "---\n"
            "document_type: research\n"
            'description: "Research into something"\n'
            "last_updated: 2026-02-17\n"
            "sources:\n"
            '  - url: "https://example.com"\n'
            '    title: "Example"\n'
            "---\n"
            "\n# Research Topic\n\n"
            "## Question\n\nWhat is the answer?\n\n"
            "## Findings\n\nThe finding.\n\n"
            "## Implications\n\nImplied.\n\n"
            "## Sources\n\n- [S](https://example.com)\n"
        )
        (art / "2026-02-17-test-research.md").write_text(
            research_content, encoding="utf-8"
        )

        result = subprocess.run(
            [sys.executable, "scripts/check_health.py", "--root", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        report = json.loads(result.stdout)
        budget = report["token_budget"]

        # Only python area, no artifact area
        area_names = [a["area"] for a in budget["areas"]]
        assert area_names == ["python"]
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_check_health_integration.py -v`
Expected: FAIL — `KeyError: 'token_budget'` (not yet in health output)

**Step 3: Commit**

```bash
git add tests/test_check_health_integration.py
git commit -m "test: add integration tests for token budget in health output"
```

---

### Task 4: Health script integration — implementation

**Files:**
- Modify: `scripts/check_health.py:34-37` (add import)
- Modify: `scripts/check_health.py:87-116` (add token budget call and merge into output)

**Step 1: Add token budget to health script**

In `scripts/check_health.py`, add the import at line 37:

```python
from wos.token_budget import estimate_token_budget
```

After the cross-validators call (line 88) and before the tier2 block (line 91), add:

```python
    # Compute token budget for context files only
    context_docs = [d for d in docs if d.path.startswith("context/")]
    token_budget = estimate_token_budget(context_docs)
    if "issue" in token_budget:
        all_issues.append(token_budget["issue"])
```

In the report dict (lines 111-116), add `token_budget`:

```python
    # Strip the issue from the budget dict (it's already in all_issues)
    budget_output = {k: v for k, v in token_budget.items() if k != "issue"}

    report = {
        "status": status,
        "files_checked": len(docs) + len(parse_issues),
        "token_budget": budget_output,
        "issues": all_issues,
        "triggers": all_triggers,
    }
```

Handle the empty-project case — add `token_budget` to the early-exit report too:

```python
    if not md_files:
        report = {
            "status": "pass",
            "files_checked": 0,
            "token_budget": {
                "total_estimated_tokens": 0,
                "warning_threshold": 40_000,
                "over_budget": False,
                "areas": [],
            },
            "issues": [],
            "triggers": [],
            "message": "No documents found. "
            "Use /wos:setup to initialize your project.",
        }
```

**Step 2: Run integration tests**

Run: `python3 -m pytest tests/test_check_health_integration.py -v`
Expected: All PASS

**Step 3: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 4: Run linter**

Run: `ruff check scripts/check_health.py wos/token_budget.py`
Expected: No issues

**Step 5: Commit**

```bash
git add scripts/check_health.py
git commit -m "feat: integrate token budget estimation into health output"
```

---

### Task 5: Final verification and cleanup

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 2: Run linter on all changed files**

Run: `ruff check wos/ tests/ scripts/`
Expected: No issues

**Step 3: Verify health output manually (if a context/ dir exists)**

Run: `python3 scripts/check_health.py | python3 -m json.tool`
Expected: JSON output with `token_budget` key containing expected structure

**Step 4: Commit any final adjustments if needed**
