---
name: Simplification Round 2
description: Implementation plan for 7 cleanup tasks - dead code removal, shared marker utility, index.py refactor, report-issue simplification, parameter shadowing fix, version consistency test, and CLAUDE.md update
---

# Simplification Round 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove dead code, reduce duplication, and tighten the codebase without changing external behavior.

**Architecture:** Seven independent cleanup tasks touching wos/ modules, tests, a skill definition, and CLAUDE.md. No new features, no new dependencies. Each task is independently mergeable.

**Tech Stack:** Python 3.9, pytest, existing wos/ package

**Branch:** `simplification-round-2` (merged to main)
**Version:** 0.2.1

---

### ~~Task 1: Remove `source_verification.py` and its tests~~ ✅

This module is 466 lines, unused by any import, and duplicates `url_checker.py`. Its test file is 555 lines (the largest test file). Removing both deletes ~1,021 lines with zero behavioral change.

**Files:**
- Delete: `wos/source_verification.py`
- Delete: `tests/test_source_verification.py`
- Modify: `CLAUDE.md:41` (remove source_verification.py bullet)
- Modify: `README.md:45` (remove source_verification.py from file tree)
- Modify: `skills/research/references/source-verification.md` (replace CLI invocation with url_checker or remove)
- Modify: `skills/research/references/research-investigate.md:29` (replace CLI invocation with url_checker or remove)

**Step 1: Verify nothing imports source_verification**

Run: `grep -r "source_verification" wos/ scripts/ skills/ tests/ --include="*.py" --include="*.md"`
Expected: Hits in `wos/source_verification.py`, `tests/test_source_verification.py`, `CLAUDE.md`, `README.md`, and two skill reference files. No production imports in `wos/` or `scripts/`.

**Step 2: Delete the module and test file**

```bash
rm wos/source_verification.py tests/test_source_verification.py
```

**Step 3: Update CLAUDE.md — remove the source_verification bullet**

In `CLAUDE.md`, remove this line:

```
  - `source_verification.py` — full source verification with title matching (pre-simplification module, kept for research skill Phase 3)
```

**Step 4: Update README.md — remove from file tree**

In `README.md`, remove this line from the project structure:

```
  source_verification.py  # Full source verification with title matching
```

**Step 5: Update skill reference files**

In `skills/research/references/source-verification.md`, replace the `python3 -m wos.source_verification` CLI invocation (line 26) with `url_checker`-based verification, or replace the entire file with instructions to use `wos.url_checker.check_urls()` for URL reachability checks (since `source_verification` added title matching on top of URL checks, and we're dropping title matching).

In `skills/research/references/research-investigate.md`, update Phase 3 (lines 28-29) to remove the `python3 -m wos.source_verification` invocation and replace with `url_checker`-based instructions. The phase should instruct using `wos.url_checker.check_urls()` for URL verification.

**Step 6: Run tests to verify nothing broke**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass, no import errors

**Step 7: Commit**

```bash
git add -A && git commit -m "chore: remove unused source_verification module and tests"
```

---

### ~~Task 2: Extract shared marker replacement utility~~ ✅

Both `agents_md.py` and `preferences.py` implement identical marker-based section replacement logic (find begin/end markers, replace between them or append if missing, consume trailing newline). Extract it into `wos/markers.py`.

**Files:**
- Create: `wos/markers.py`
- Modify: `wos/agents_md.py`
- Modify: `wos/preferences.py`
- Create: `tests/test_markers.py`

**Step 1: Write failing tests for the shared utility**

Create `tests/test_markers.py`:

```python
"""Tests for wos/markers.py — shared marker replacement utility."""

from __future__ import annotations


class TestReplaceMarkerSection:
    def test_replaces_between_existing_markers(self) -> None:
        from wos.markers import replace_marker_section

        content = (
            "Before.\n\n"
            "<!-- begin -->\nold stuff\n<!-- end -->\n\n"
            "After.\n"
        )
        result = replace_marker_section(
            content, "<!-- begin -->", "<!-- end -->", "new stuff\n"
        )
        assert "old stuff" not in result
        assert "new stuff" in result
        assert "Before." in result
        assert "After." in result

    def test_appends_when_no_markers(self) -> None:
        from wos.markers import replace_marker_section

        content = "# Header\n\nExisting content.\n"
        result = replace_marker_section(
            content, "<!-- begin -->", "<!-- end -->", "new section\n"
        )
        assert "# Header" in result
        assert "Existing content." in result
        assert "new section" in result

    def test_consumes_trailing_newline_after_end_marker(self) -> None:
        from wos.markers import replace_marker_section

        content = "Before.\n<!-- begin -->\nold\n<!-- end -->\nAfter.\n"
        result = replace_marker_section(
            content, "<!-- begin -->", "<!-- end -->", "new\n"
        )
        # Should not produce double newlines where marker was
        assert "new\nAfter." in result

    def test_handles_empty_content(self) -> None:
        from wos.markers import replace_marker_section

        result = replace_marker_section(
            "", "<!-- begin -->", "<!-- end -->", "section\n"
        )
        assert "section" in result
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_markers.py -v`
Expected: FAIL (module does not exist)

**Step 3: Implement the shared utility**

Create `wos/markers.py`:

```python
"""Shared marker-based section replacement for managed file sections.

Provides a single function for replacing content between marker comments
in text files. Used by agents_md.py and preferences.py.
"""

from __future__ import annotations


def replace_marker_section(
    content: str,
    begin_marker: str,
    end_marker: str,
    section: str,
) -> str:
    """Replace or append a marker-delimited section in text content.

    If both markers exist, replaces everything between them (inclusive).
    If markers don't exist, appends the section to the end.

    Args:
        content: The existing file content.
        begin_marker: The opening marker string.
        end_marker: The closing marker string.
        section: The new section content (should include markers if needed).

    Returns:
        Updated content with the new section.
    """
    begin_idx = content.find(begin_marker)
    end_idx = content.find(end_marker)

    if begin_idx != -1 and end_idx != -1:
        end_idx += len(end_marker)
        # Consume trailing newline if present
        if end_idx < len(content) and content[end_idx] == "\n":
            end_idx += 1
        return content[:begin_idx] + section + content[end_idx:]

    # Append
    return content.rstrip("\n") + "\n\n" + section
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_markers.py -v`
Expected: All PASS

**Step 5: Refactor `agents_md.py` to use shared utility**

Replace the marker replacement logic in `update_agents_md` (lines 104-116) with:

```python
def update_agents_md(
    content: str,
    areas: List[Dict[str, str]],
    preferences: Optional[List[str]] = None,
) -> str:
    """Replace or append the WOS section in AGENTS.md content.

    If markers exist, replaces the content between them (inclusive).
    If markers don't exist, appends the section to the end.
    Content outside markers is never touched.

    Args:
        content: The existing AGENTS.md content.
        areas: List of dicts with 'name' and 'path' keys.
        preferences: Optional list of preference strings.

    Returns:
        Updated AGENTS.md content with the new WOS section.
    """
    from wos.markers import replace_marker_section

    section = render_wos_section(areas, preferences)
    return replace_marker_section(content, BEGIN_MARKER, END_MARKER, section)
```

**Step 6: Run agents_md tests to verify behavior unchanged**

Run: `python3 -m pytest tests/test_agents_md.py -v`
Expected: All PASS

**Step 7: Refactor `preferences.py` to use shared utility**

Replace the marker replacement logic in `update_preferences` (lines 139-160) with:

```python
def update_preferences(file_path: str, prefs: Dict[str, str]) -> None:
    """Write communication preferences to CLAUDE.md using markers.

    Creates the file if it doesn't exist. Replaces existing preferences
    section if markers are found. Appends if no markers exist.
    """
    from wos.markers import replace_marker_section

    path = Path(file_path)
    rendered = render_preferences(prefs)

    section = (
        f"{COMM_MARKER_BEGIN}\n"
        f"## Communication\n"
        f"\n"
        f"{rendered}\n"
        f"\n"
        f"{COMM_MARKER_END}\n"
    )

    if not path.exists():
        path.write_text(section, encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    updated = replace_marker_section(content, COMM_MARKER_BEGIN, COMM_MARKER_END, section)
    path.write_text(updated, encoding="utf-8")
```

**Step 8: Run preferences tests to verify behavior unchanged**

Run: `python3 -m pytest tests/test_preferences.py -v`
Expected: All PASS

**Step 9: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 10: Commit**

```bash
git add wos/markers.py tests/test_markers.py wos/agents_md.py wos/preferences.py
git commit -m "refactor: extract shared marker replacement into wos/markers.py"
```

---

### ~~Task 3: Make `index.py` use `document.py` for frontmatter extraction~~ ✅

`index.py` has its own `_extract_description()` (lines 20-57) that independently parses YAML frontmatter. Replace it with a call to `parse_document()` from `document.py`.

**Note:** The `index.py` docstring (lines 7-9) states this independence is intentional: "This module is intentionally independent of wos.document — it uses yaml.safe_load directly so it can be used without the full document parsing pipeline." We are overriding this decision because: (1) `parse_document()` is lightweight and has no heavy dependencies, (2) the duplicated frontmatter parsing is a maintenance burden, and (3) the "full document parsing pipeline" concern is moot since `parse_document()` is just YAML parsing + a dataclass. Remove the independence comment as part of this change.

**Files:**
- Modify: `wos/index.py`
- Existing tests: `tests/test_index.py` (no changes needed — tests verify behavior, not implementation)

**Step 1: Run existing index tests to establish baseline**

Run: `python3 -m pytest tests/test_index.py -v`
Expected: All PASS

**Step 2: Rewrite `_extract_description` in `index.py`**

Replace `_extract_description()` (lines 20-57) and the `import yaml` line (line 17) with:

```python
from wos.document import parse_document


def _extract_description(file_path: Path) -> Optional[str]:
    """Extract description from YAML frontmatter of a markdown file.

    Args:
        file_path: Path to a .md file.

    Returns:
        The description string, or None if no frontmatter or no
        description field is present.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        doc = parse_document(str(file_path), text)
    except ValueError:
        return None

    return doc.description if doc.description else None
```

Also remove the docstring lines (7-9) about intentional independence from `wos.document`.

**Step 3: Run index tests to verify behavior unchanged**

Run: `python3 -m pytest tests/test_index.py -v`
Expected: All PASS (same behavior, different implementation)

**Step 4: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add wos/index.py
git commit -m "refactor: index.py uses document.parse_document for frontmatter extraction"
```

---

### ~~Task 4: Fix parameter shadowing in `validators.py`~~ ✅

The `validate_file()` function (line 155) has a parameter `check_urls` that shadows the imported function `check_urls` from `url_checker.py` (line 18). Rename the parameter to `verify_urls`.

**Files:**
- Modify: `wos/validators.py:155-156,193,200,233`
- Modify: `tests/test_validators.py:260,270,297` (update call sites)
- Modify: `scripts/audit.py` (update call site)

**Step 1: Run existing tests to establish baseline**

Run: `python3 -m pytest tests/test_validators.py -v`
Expected: All PASS

**Step 2: Rename the parameter in `validators.py`**

In `validate_file()` (line 155-156), rename `check_urls` parameter to `verify_urls`:

```python
def validate_file(
    path: Path, root: Path, verify_urls: bool = True
) -> List[dict]:
```

Update the usage on line 193:

```python
    if verify_urls:
```

In `validate_project()` (line 199-200), rename the parameter the same way:

```python
def validate_project(
    root: Path, verify_urls: bool = True
) -> List[dict]:
```

Update the call site on line 233:

```python
                issues.extend(validate_file(file_path, root, verify_urls=verify_urls))
```

**Step 3: Update test call sites**

In `tests/test_validators.py`, update three call sites:

Line 260:
```python
        issues = validate_file(md_file, tmp_path, verify_urls=False)
```

Line 270:
```python
        issues = validate_file(md_file, tmp_path, verify_urls=False)
```

Line 297:
```python
        issues = validate_project(tmp_path, verify_urls=False)
```

**Step 4: Update scripts/audit.py call site**

In `scripts/audit.py`, find the call to `validate_project` and update the keyword argument from `check_urls=` to `verify_urls=`.

**Step 5: Run tests to verify**

Run: `python3 -m pytest tests/test_validators.py -v`
Expected: All PASS

**Step 6: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add wos/validators.py tests/test_validators.py scripts/audit.py
git commit -m "refactor: rename check_urls parameter to verify_urls to avoid shadowing"
```

---

### ~~Task 5: Add version consistency test~~ ✅

Version is maintained in 3 files: `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`. Add a test that asserts all three match, catching drift at test time.

**Files:**
- Create: `tests/test_version.py`

**Step 1: Write the test**

Create `tests/test_version.py`:

```python
"""Tests for version consistency across configuration files."""

from __future__ import annotations

import json
from pathlib import Path


def _project_root() -> Path:
    """Return the project root directory (parent of tests/)."""
    return Path(__file__).resolve().parent.parent


def test_version_consistent_across_config_files() -> None:
    """pyproject.toml, plugin.json, and marketplace.json must have matching versions."""
    root = _project_root()

    # pyproject.toml
    pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    pyproject_version = None
    for line in pyproject_text.splitlines():
        if line.strip().startswith("version"):
            pyproject_version = line.split("=", 1)[1].strip().strip('"')
            break
    assert pyproject_version is not None, "No version found in pyproject.toml"

    # plugin.json
    plugin_data = json.loads(
        (root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    plugin_version = plugin_data["version"]

    # marketplace.json
    marketplace_data = json.loads(
        (root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    marketplace_version = marketplace_data["plugins"][0]["version"]

    assert pyproject_version == plugin_version, (
        f"pyproject.toml ({pyproject_version}) != "
        f"plugin.json ({plugin_version})"
    )
    assert pyproject_version == marketplace_version, (
        f"pyproject.toml ({pyproject_version}) != "
        f"marketplace.json ({marketplace_version})"
    )
```

**Step 2: Run the test**

Run: `python3 -m pytest tests/test_version.py -v`
Expected: PASS (all three currently say 0.2.0)

**Step 3: Commit**

```bash
git add tests/test_version.py
git commit -m "test: add version consistency check across config files"
```

---

### ~~Task 6: Simplify report-issue skill~~ ✅

Trim the 6-phase workflow to 4 phases and reduce template boilerplate. Merge "Classify" into "Gather Context", merge "Preview" into "Draft".

**Files:**
- Modify: `skills/report-issue/SKILL.md`
- Modify: `skills/report-issue/references/report-issue-submit.md`
- Modify: `skills/report-issue/references/issue-templates.md`

**Step 1: Rewrite `report-issue-submit.md` to 4 phases**

Replace `skills/report-issue/references/report-issue-submit.md` with a streamlined version:

- **Phase 1: Check Prerequisites** (keep as-is, it's short)
- **Phase 2: Gather Context & Classify** (merge phases 2+3 — ask what happened, auto-gather env info, classify type inline)
- **Phase 3: Draft & Preview** (merge phases 4+5 — draft from template, show preview, ask for approval. Keep the framing rule as a brief note, drop the full quality checklist table)
- **Phase 4: Submit** (keep as-is)

Key reductions:
- Remove the detailed "Consumer-specific details to catch and generalize" list (4 bullets)
- Remove the quality checklist table (6-row table) — replace with a single sentence: "Verify the issue is self-contained and uses generic framing before showing preview."
- Remove the preview format box (the `───` border template)

**Step 2: Simplify issue templates**

In `skills/report-issue/references/issue-templates.md`:
- **Bug Report:** Keep Description, Steps to Reproduce (merge MRE into this), Expected vs Actual, Environment. Remove the separate "Minimum Reproducible Example" section header.
- **Feature Request:** Keep Problem, Proposed Solution, Environment. Remove Evaluation section (Test Fixtures and Pass Criteria tables), remove Alternatives Considered, remove Why This Matters. Move Scope/Non-Goals into Proposed Solution as sub-bullets.
- **General Feedback:** Keep as-is (already minimal).

**Step 3: Update SKILL.md if needed**

Review `skills/report-issue/SKILL.md` — it references "steps in `references/report-issue-submit.md`" which still holds. No changes needed unless wording references specific phase numbers.

**Step 4: Commit**

```bash
git add skills/report-issue/
git commit -m "docs: simplify report-issue skill from 6 phases to 4"
```

---

### ~~Task 7: Update CLAUDE.md architecture section~~ ✅

After all tasks are complete, update CLAUDE.md to reflect changes:
- Remove `source_verification.py` from package listing (done in Task 1)
- Add `markers.py` to package listing
- Update the module count to 7 (currently says "~5" but 7 are listed; after removing source_verification and adding markers, still 7)

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update the package structure section**

Add `markers.py` bullet to the package listing:

```
  - `markers.py` — shared marker-based section replacement
```

Update the count: `wos/` — importable Python package (7 modules)

**Step 2: Run full test suite one final time**

Run: `python3 -m pytest tests/ -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md architecture for simplification round 2"
```
