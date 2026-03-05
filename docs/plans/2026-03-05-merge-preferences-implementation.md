---
name: "Merge Preferences Implementation Plan"
description: "Step-by-step implementation for rolling /wos:preferences into /wos:init and consolidating on AGENTS.md"
type: plan
related:
  - docs/plans/2026-03-05-merge-preferences-design.md
---

# Merge Preferences Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Roll `/wos:preferences` into `/wos:init`, make AGENTS.md the single delivery mechanism for all WOS-managed content, and reduce skill count from 9 to 8.

**Architecture:** Preferences feed through `render_wos_section()` in `agents_md.py` instead of writing to CLAUDE.md with separate markers. The `update_preferences.py` script takes `--root` and re-renders the full AGENTS.md WOS section. `reindex.py` preserves existing preferences when re-rendering. Init gains a preferences capture step and a CLAUDE.md pointer step.

**Tech Stack:** Python 3.9 (stdlib only), pytest, markdown skill files

**Branch:** `feat/merge-preferences`

---

### Task 1: Add `extract_preferences()` to `agents_md.py`

**Files:**
- Modify: `wos/agents_md.py`
- Test: `tests/test_agents_md.py`

**Step 1: Write the failing tests**

Add a new test class in `tests/test_agents_md.py` after `TestRenderDocumentStandards`:

```python
class TestExtractPreferences:
    def test_extracts_preferences_from_wos_section(self) -> None:
        from wos.agents_md import extract_preferences, render_wos_section

        prefs = ["**Directness:** Be direct.", "**Tone:** Keep it casual."]
        content = f"# AGENTS.md\n\n{render_wos_section(areas=[], preferences=prefs)}"
        result = extract_preferences(content)
        assert result == prefs

    def test_returns_empty_when_no_markers(self) -> None:
        from wos.agents_md import extract_preferences

        result = extract_preferences("# AGENTS.md\n\nNo WOS section here.\n")
        assert result == []

    def test_returns_empty_when_no_preferences_section(self) -> None:
        from wos.agents_md import extract_preferences, render_wos_section

        content = render_wos_section(areas=[], preferences=None)
        result = extract_preferences(content)
        assert result == []

    def test_preserves_preference_content_exactly(self) -> None:
        from wos.agents_md import extract_preferences, render_wos_section

        prefs = [
            "**Directness:** Be direct. State problems and disagreements "
            "plainly without hedging or softening."
        ]
        content = render_wos_section(areas=[], preferences=prefs)
        result = extract_preferences(content)
        assert result == prefs
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_agents_md.py::TestExtractPreferences -v`
Expected: FAIL — `extract_preferences` not found

**Step 3: Implement `extract_preferences()`**

In `wos/agents_md.py`, add after the `render_wos_section()` function (after line 144):

```python
def extract_preferences(content: str) -> List[str]:
    """Extract preference strings from an AGENTS.md WOS section.

    Parses the ``### Preferences`` subsection between WOS markers and
    returns the list of preference strings (without ``- `` bullet prefix).
    Used by reindex and update_preferences to preserve existing preferences.

    Args:
        content: Full AGENTS.md file content.

    Returns:
        List of preference strings, or empty list if none found.
    """
    begin_idx = content.find(BEGIN_MARKER)
    end_idx = content.find(END_MARKER)
    if begin_idx == -1 or end_idx == -1:
        return []

    wos_section = content[begin_idx:end_idx]
    lines = wos_section.split("\n")

    in_preferences = False
    prefs: List[str] = []
    for line in lines:
        if line.strip() == "### Preferences":
            in_preferences = True
            continue
        if in_preferences:
            if line.startswith("### ") or line.startswith("<!--"):
                break
            if line.startswith("- "):
                prefs.append(line[2:])

    return prefs
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_agents_md.py::TestExtractPreferences -v`
Expected: PASS

**Step 5: Run full agents_md test suite**

Run: `uv run python -m pytest tests/test_agents_md.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add wos/agents_md.py tests/test_agents_md.py
git commit -m "feat: add extract_preferences() to agents_md.py"
```

---

### Task 2: Change `render_preferences()` return type and remove CLAUDE.md writer

**Files:**
- Modify: `wos/preferences.py`
- Modify: `tests/test_preferences.py`

**Step 1: Update tests for new return type**

In `tests/test_preferences.py`, replace `TestRenderPreferences` (lines 31-69) with:

```python
class TestRenderPreferences:
    def test_renders_all_dimensions(self) -> None:
        from wos.preferences import render_preferences

        prefs = {
            "directness": "blunt",
            "verbosity": "terse",
            "depth": "just-answers",
            "expertise": "expert",
            "tone": "casual",
        }
        result = render_preferences(prefs)
        assert isinstance(result, list)
        assert len(result) == 5
        assert any("Directness" in line for line in result)
        assert any("Verbosity" in line for line in result)
        assert any("Depth" in line for line in result)
        assert any("Expertise" in line for line in result)
        assert any("Tone" in line for line in result)

    def test_renders_subset_of_dimensions(self) -> None:
        from wos.preferences import render_preferences

        prefs = {"directness": "blunt", "tone": "formal"}
        result = render_preferences(prefs)
        assert len(result) == 2
        assert any("Directness" in line for line in result)
        assert any("Tone" in line for line in result)
        assert not any("Verbosity" in line for line in result)

    def test_no_bullet_prefix(self) -> None:
        from wos.preferences import render_preferences

        result = render_preferences({"directness": "blunt"})
        assert not result[0].startswith("- ")
        assert result[0].startswith("**Directness:**")

    def test_invalid_dimension_raises(self) -> None:
        from wos.preferences import render_preferences

        with pytest.raises(ValueError, match="Unknown dimension"):
            render_preferences({"nonexistent": "value"})

    def test_invalid_level_raises(self) -> None:
        from wos.preferences import render_preferences

        with pytest.raises(ValueError, match="Unknown level"):
            render_preferences({"directness": "nonexistent"})

    def test_compatible_with_render_wos_section(self) -> None:
        from wos.agents_md import render_wos_section
        from wos.preferences import render_preferences

        prefs = render_preferences({"directness": "blunt"})
        result = render_wos_section(areas=[], preferences=prefs)
        assert "### Preferences" in result
        assert "- **Directness:**" in result
```

**Step 2: Delete `TestUpdatePreferences` class**

Remove the entire `TestUpdatePreferences` class (lines 75-153 in the original
`tests/test_preferences.py`). These tests cover `update_preferences()` and
`COMM_MARKER_BEGIN/END` which are being deleted.

**Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_preferences.py -v`
Expected: FAIL — return type is `str` not `list`, and bullet prefix present

**Step 4: Update `render_preferences()` and remove dead code**

In `wos/preferences.py`:

1. Change `render_preferences()` (lines 97-121) to return `List[str]`:

```python
def render_preferences(prefs: Dict[str, str]) -> List[str]:
    """Render preference dimensions as instruction strings.

    Each string is formatted as ``**Dimension:** instruction`` without
    a bullet prefix. Pass the returned list to
    ``render_wos_section(preferences=...)`` which adds bullets.

    Args:
        prefs: Mapping of dimension name to level.

    Returns:
        List of formatted instruction strings.

    Raises:
        ValueError: If an unknown dimension or level is provided.
    """
    result: List[str] = []
    for dim, level in prefs.items():
        if dim not in DIMENSIONS:
            raise ValueError(f"Unknown dimension: {dim}")
        if level not in DIMENSIONS[dim]:
            raise ValueError(
                f"Unknown level '{level}' for dimension '{dim}'. "
                f"Valid levels: {DIMENSIONS[dim]}"
            )
        instruction = DIMENSION_INSTRUCTIONS[(dim, level)]
        display = _DISPLAY_NAMES[dim]
        result.append(f"**{display}:** {instruction}")
    return result
```

2. Delete `COMM_MARKER_BEGIN` and `COMM_MARKER_END` (lines 14-15).

3. Delete the entire `update_preferences()` function (lines 127-155).

4. Update the module docstring (line 1-5) to:

```python
"""Communication preferences — dimension mapping and rendering.

Maps user communication preferences to structured dimensions and
renders them as instruction strings for AGENTS.md.
"""
```

**Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_preferences.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add wos/preferences.py tests/test_preferences.py
git commit -m "refactor: change render_preferences() to return List[str], remove CLAUDE.md writer"
```

---

### Task 3: Update `reindex.py` to preserve preferences

**Files:**
- Modify: `scripts/reindex.py:99-114`
- Test: `tests/test_agents_md.py`

**Step 1: Write the failing test**

Add a new test in `tests/test_agents_md.py` inside `TestReindexUpdatesAgentsMd`:

```python
    def test_reindex_preserves_existing_preferences(self, tmp_path: Path) -> None:
        from wos.agents_md import BEGIN_MARKER, END_MARKER, render_wos_section
        from wos.index import generate_index

        # Set up a project with an area
        area_dir = tmp_path / "docs" / "context" / "api"
        area_dir.mkdir(parents=True)
        (area_dir / "_index.md").write_text(
            generate_index(area_dir, preamble="API documentation")
        )
        (area_dir / "endpoints.md").write_text(
            "---\nname: Endpoints\ndescription: API endpoints\n---\n"
        )

        # Create AGENTS.md with preferences already set
        prefs = ["**Directness:** Be direct.", "**Tone:** Keep it casual."]
        agents_path = tmp_path / "AGENTS.md"
        agents_content = f"# AGENTS.md\n\n{render_wos_section(areas=[], preferences=prefs)}"
        agents_path.write_text(agents_content)

        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "reindex.py"),
                "--root", str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        updated = agents_path.read_text()
        # Areas should be updated
        assert "| API documentation | docs/context/api |" in updated
        # Preferences should be preserved
        assert "### Preferences" in updated
        assert "- **Directness:** Be direct." in updated
        assert "- **Tone:** Keep it casual." in updated
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_agents_md.py::TestReindexUpdatesAgentsMd::test_reindex_preserves_existing_preferences -v`
Expected: FAIL — preferences are lost because `_update_agents_md_areas` doesn't pass them

**Step 3: Update `_update_agents_md_areas()` in `reindex.py`**

Replace the `_update_agents_md_areas` function (lines 99-114) with:

```python
def _update_agents_md_areas(root: Path) -> None:
    """Auto-update the AGENTS.md areas table from disk state."""
    from wos.agents_md import discover_areas, extract_preferences, update_agents_md

    agents_path = root / "AGENTS.md"
    if not agents_path.is_file():
        return

    areas = discover_areas(root)
    content = agents_path.read_text(encoding="utf-8")
    preferences = extract_preferences(content)
    updated = update_agents_md(content, areas, preferences=preferences or None)
    if updated != content:
        agents_path.write_text(updated, encoding="utf-8")
        print(f"Updated AGENTS.md areas table ({len(areas)} areas).")
    else:
        print("AGENTS.md areas table already up to date.")
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_agents_md.py::TestReindexUpdatesAgentsMd -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run python -m pytest tests/test_agents_md.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add scripts/reindex.py tests/test_agents_md.py
git commit -m "fix: preserve preferences when reindex updates AGENTS.md"
```

---

### Task 4: Rework `scripts/update_preferences.py`

**Files:**
- Modify: `scripts/update_preferences.py`
- Modify: `tests/test_update_preferences.py`

**Step 1: Rewrite the test file**

Replace `tests/test_update_preferences.py` entirely:

```python
"""Tests for scripts/update_preferences.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from wos.agents_md import BEGIN_MARKER, END_MARKER
from wos.index import generate_index

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestUpdatePreferencesHelp:
    def test_no_args_shows_usage(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "update_preferences.py")],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode != 0
        assert "usage" in result.stderr.lower()


class TestUpdatePreferencesWritesAgentsMd:
    def test_writes_preferences_to_agents_md(self, tmp_path: Path) -> None:
        # Set up minimal project structure
        docs_dir = tmp_path / "docs" / "context"
        docs_dir.mkdir(parents=True)

        # Create AGENTS.md with WOS markers
        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text(
            f"# AGENTS.md\n\n{BEGIN_MARKER}\nold\n{END_MARKER}\n"
        )

        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "update_preferences.py"),
                "--root", str(tmp_path),
                "directness=blunt", "tone=casual",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        content = agents_path.read_text()
        assert "### Preferences" in content
        assert "**Directness:**" in content
        assert "**Tone:**" in content
        assert BEGIN_MARKER in content
        assert END_MARKER in content

    def test_preserves_areas(self, tmp_path: Path) -> None:
        # Set up project with an area
        area_dir = tmp_path / "docs" / "context" / "api"
        area_dir.mkdir(parents=True)
        (area_dir / "_index.md").write_text(
            generate_index(area_dir, preamble="API docs")
        )

        agents_path = tmp_path / "AGENTS.md"
        agents_path.write_text(f"# AGENTS.md\n\n{BEGIN_MARKER}\nold\n{END_MARKER}\n")

        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "update_preferences.py"),
                "--root", str(tmp_path),
                "directness=blunt",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        content = agents_path.read_text()
        assert "| API docs | docs/context/api |" in content
        assert "**Directness:**" in content

    def test_creates_agents_md_if_missing(self, tmp_path: Path) -> None:
        docs_dir = tmp_path / "docs" / "context"
        docs_dir.mkdir(parents=True)

        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "update_preferences.py"),
                "--root", str(tmp_path),
                "verbosity=terse",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        agents_path = tmp_path / "AGENTS.md"
        assert agents_path.exists()
        content = agents_path.read_text()
        assert "**Verbosity:**" in content
        assert BEGIN_MARKER in content
```

**Step 2: Rewrite the script**

Replace `scripts/update_preferences.py` entirely:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Update communication preferences in AGENTS.md.

Usage:
    uv run scripts/update_preferences.py --root . key=value [key=value ...]

Example:
    uv run scripts/update_preferences.py --root . directness=blunt verbosity=terse
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update communication preferences in AGENTS.md.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "preferences",
        nargs="+",
        metavar="key=value",
        help="Preference key=value pairs (e.g., directness=blunt)",
    )
    args = parser.parse_args()

    from wos.agents_md import discover_areas, update_agents_md
    from wos.preferences import render_preferences

    root = Path(args.root).resolve()

    prefs = {}
    for arg in args.preferences:
        if "=" not in arg:
            parser.error(f"Invalid preference: {arg!r} (expected key=value)")
        key, value = arg.split("=", 1)
        prefs[key] = value

    rendered = render_preferences(prefs)
    areas = discover_areas(root)

    agents_path = root / "AGENTS.md"
    if agents_path.is_file():
        content = agents_path.read_text(encoding="utf-8")
    else:
        content = "# AGENTS.md\n"

    updated = update_agents_md(content, areas, preferences=rendered)
    agents_path.write_text(updated, encoding="utf-8")
    print(f"Updated preferences in {agents_path}")


if __name__ == "__main__":
    main()
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/test_update_preferences.py -v`
Expected: PASS

**Step 4: Run full test suite**

Run: `uv run python -m pytest tests/ -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add scripts/update_preferences.py tests/test_update_preferences.py
git commit -m "refactor: update_preferences.py writes to AGENTS.md via --root"
```

---

### Task 5: Update `/wos:init` skill and move references

**Files:**
- Modify: `skills/init/SKILL.md`
- Move: `skills/preferences/references/capture-workflow.md` → `skills/init/references/capture-workflow.md`

**Step 1: Create the references directory and move the file**

```bash
mkdir -p skills/init/references
cp skills/preferences/references/capture-workflow.md skills/init/references/capture-workflow.md
```

**Step 2: Update the capture workflow reference**

Edit `skills/init/references/capture-workflow.md` — replace step 4 (lines 41-46)
from:

```markdown
4. **Write to CLAUDE.md**

   After confirmation, write the preferences using the Python module:

   ```bash
   uv run <plugin-scripts-dir>/update_preferences.py CLAUDE.md directness=blunt verbosity=terse
   ```

   Report what was written and where.
```

to:

```markdown
4. **Write to AGENTS.md**

   After confirmation, write the preferences using the Python module:

   ```bash
   uv run <plugin-scripts-dir>/update_preferences.py --root . directness=blunt verbosity=terse
   ```

   This updates the `### Preferences` subsection inside the WOS-managed
   section of AGENTS.md.
```

**Step 3: Rewrite `skills/init/SKILL.md`**

Replace the entire file:

```markdown
---
name: wos:init
description: >
  Initialize or update WOS project context. Use when starting a new project
  with WOS, or re-run to verify and repair an existing setup. Idempotent —
  safe to run multiple times.
argument-hint: ""
user-invocable: true
references:
  - ../_shared/references/preflight.md
  - references/capture-workflow.md
---

# Init WOS

Initialize or update WOS project context. Idempotent — safe to re-run.

**Prerequisite:** Before running any `uv run` command below, follow the
preflight check in the [preflight reference](../_shared/references/preflight.md).

## Workflow

### 1. Check current state

Check which parts of the WOS structure already exist:

- `docs/context/` directory
- `docs/research/` directory
- `docs/plans/` directory
- `AGENTS.md` with WOS markers (`<!-- wos:begin -->` / `<!-- wos:end -->`)
- `### Preferences` subsection in the WOS-managed section
- `CLAUDE.md` with `@AGENTS.md` reference

### 2. Create missing directories

Create any missing directories:

```
docs/
  context/
  research/
  plans/
```

### 3. Reindex

Run: `uv run <plugin-scripts-dir>/reindex.py --root .`

This creates `_index.md` files in each directory and updates the AGENTS.md
areas table if AGENTS.md exists.

### 4. Update AGENTS.md

If `AGENTS.md` does not exist, create it with a `# AGENTS.md` heading.

Write the WOS-managed section between `<!-- wos:begin -->` / `<!-- wos:end -->`
markers. This section includes context navigation, areas table, file metadata
format, document standards, and preferences. The markers enable automated
updates — never place WOS-managed content outside them.

If markers already exist, the section is replaced with the latest version
(picking up any new standards or areas).

### 5. Preferences

Capture or review communication preferences.

**If no `### Preferences` subsection exists** in the WOS section:

Run the full capture workflow in `references/capture-workflow.md`:
1. Ask the freeform communication style question
2. Map response to dimensions
3. Confirm with user
4. Write to AGENTS.md via `uv run <plugin-scripts-dir>/update_preferences.py --root .`

**If preferences already exist:**

Show the current settings to the user. Ask: "Want to change any of these?"
- If yes → re-run the capture workflow
- If no → move on

### 6. CLAUDE.md pointer

If `CLAUDE.md` does not exist, create it with:

```markdown
@AGENTS.md
```

If `CLAUDE.md` exists but does not contain `@AGENTS.md`, add the reference
at the top of the file.

### 7. Report

Report what was done:

- **Created:** list any directories or files that were created
- **Updated:** note if AGENTS.md WOS section was refreshed
- **Preferences:** note if preferences were set or unchanged
- **CLAUDE.md:** note if pointer was added or already present
- **Already present:** note anything that was already in place

If everything was already set up, confirm: "WOS is up to date. No changes needed."
```

**Step 4: Verify the files**

Read back both files. Confirm:
- `SKILL.md` frontmatter has `references:` including `capture-workflow.md`
- Capture workflow references `update_preferences.py --root .` (not `CLAUDE.md`)

**Step 5: Commit**

```bash
git add skills/init/SKILL.md skills/init/references/capture-workflow.md
git commit -m "feat: add preferences capture and CLAUDE.md pointer to /wos:init"
```

---

### Task 6: Delete `skills/preferences/`

**Files:**
- Delete: `skills/preferences/SKILL.md`
- Delete: `skills/preferences/references/capture-workflow.md`

**Step 1: Remove the directory**

```bash
rm -rf skills/preferences/
```

**Step 2: Verify it's gone**

```bash
ls skills/preferences/ 2>&1
```
Expected: "No such file or directory"

**Step 3: Commit**

```bash
git add -A skills/preferences/
git commit -m "chore: remove /wos:preferences skill (merged into /wos:init)"
```

---

### Task 7: Update CLAUDE.md and markers.py docstring

**Files:**
- Modify: `CLAUDE.md:58,65,84,88,100`
- Modify: `wos/markers.py:4`

**Step 1: Update CLAUDE.md**

Five changes:

1. Line 58: Update preferences.py description:
   ```
   - `preferences.py` — communication preferences capture
   ```
   →
   ```
   - `preferences.py` — communication preferences dimensions and rendering
   ```

2. Line 65: Update update_preferences.py description:
   ```
   - `update_preferences.py` — communication preferences updates
   ```
   →
   ```
   - `update_preferences.py` — write communication preferences to AGENTS.md
   ```

3. Line 84: Already mentions "communication preferences" in Navigation section — no change needed.

4. Line 88: Update skill count and remove preferences row. Change:
   ```
   Prefix: `/wos:` (e.g., `/wos:init`, `/wos:audit`). 9 skills:
   ```
   →
   ```
   Prefix: `/wos:` (e.g., `/wos:init`, `/wos:audit`). 8 skills:
   ```

5. Line 100: Remove the preferences row:
   ```
   | `/wos:preferences` | Capture communication preferences |
   ```
   Delete this entire line.

**Step 2: Update `wos/markers.py` docstring**

Line 4: Change:
```
in text files. Used by agents_md.py and preferences.py.
```
→
```
in text files. Used by agents_md.py.
```

**Step 3: Verify no stray references**

Run: `grep -rn "wos:preferences\|/preferences" skills/ CLAUDE.md --include="*.md" | grep -v __pycache__`
Expected: No results

**Step 4: Commit**

```bash
git add CLAUDE.md wos/markers.py
git commit -m "docs: update CLAUDE.md for preferences merge, fix markers.py docstring"
```

---

### Task 8: Run full test suite and verify

**Step 1: Run all tests**

Run: `uv run python -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Verify no references to old skill remain**

Run: `grep -rn "wos:preferences\|COMM_MARKER\|wos:communication" wos/ tests/ scripts/ skills/ CLAUDE.md --include="*.py" --include="*.md" | grep -v __pycache__`
Expected: No results

**Step 3: Verify preferences skill directory is gone**

```bash
ls skills/preferences/ 2>&1
```
Expected: "No such file or directory"

**Step 4: Count skills**

```bash
find skills/ -name "SKILL.md" | wc -l
```
Expected: 8

**Step 5: Commit if any fixups needed**

If any stray references were found and fixed, commit them.

---

## Branch / PR

- Branch: `feat/merge-preferences`
- PR: TBD — create after all tasks complete
