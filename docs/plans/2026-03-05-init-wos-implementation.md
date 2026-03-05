---
name: "init-wos Implementation Plan"
description: "Step-by-step implementation for replacing /create with /init-wos and adding document standards to AGENTS.md"
type: plan
related:
  - docs/plans/2026-03-05-init-wos-design.md
---

# init-wos Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace `/wos:create` with `/init-wos` — a focused, idempotent bootstrap skill — and move document standards into AGENTS.md as the single source of truth.

**Architecture:** Expand `render_wos_section()` in `wos/agents_md.py` with a Document Standards subsection. Create a new `skills/init-wos/SKILL.md` that bootstraps and verifies WOS setup. Remove `skills/create/`. Deduplicate convention guidance from `/distill` and `/research` with one-liner references to AGENTS.md.

**Tech Stack:** Python 3.9 (stdlib only), pytest, markdown skill files

**Branch:** `feat/init-wos`

---

### Task 1: Add Document Standards to `render_wos_section()`

**Files:**
- Modify: `wos/agents_md.py:57-122`
- Test: `tests/test_agents_md.py`

**Step 1: Write the failing test**

Add a new test class in `tests/test_agents_md.py` after `TestRenderLostInTheMiddleCue`:

```python
class TestRenderDocumentStandards:
    def test_renders_document_standards_section(self) -> None:
        from wos.agents_md import render_wos_section

        result = render_wos_section(areas=[])
        assert "### Document Standards" in result

    def test_renders_structure_guidance(self) -> None:
        from wos.agents_md import render_wos_section

        result = render_wos_section(areas=[])
        assert "Key insights first" in result
        assert "detail in the middle" in result
        assert "takeaways at the bottom" in result

    def test_renders_word_count_guidance(self) -> None:
        from wos.agents_md import render_wos_section

        result = render_wos_section(areas=[])
        assert "200-800 words" in result

    def test_renders_linking_guidance(self) -> None:
        from wos.agents_md import render_wos_section

        result = render_wos_section(areas=[])
        assert "bidirectional" in result.lower()

    def test_renders_one_concept_per_file(self) -> None:
        from wos.agents_md import render_wos_section

        result = render_wos_section(areas=[])
        assert "one concept per file" in result.lower()
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_agents_md.py::TestRenderDocumentStandards -v`
Expected: FAIL — "Document Standards" not in output

**Step 3: Add Document Standards subsection to `render_wos_section()`**

In `wos/agents_md.py`, add a new block in `render_wos_section()` between the
File Metadata Format section (line 112) and the Preferences section (line 114).

```python
    # ── Document Standards ────────────────────────────────────────
    lines.append("")
    lines.append("### Document Standards")
    lines.append("")
    lines.append(
        "**Structure:** Key insights first, detailed explanation "
        "in the middle, takeaways at the bottom."
    )
    lines.append(
        "LLMs lose attention mid-document — first and last sections "
        "are what agents retain."
    )
    lines.append("")
    lines.append("**Conventions:**")
    lines.append("- Context files target 200-800 words. Over 800, consider splitting.")
    lines.append(
        "- One concept per file. Multiple distinct topics should be separate files."
    )
    lines.append(
        "- Link bidirectionally — if A references B in `related`, B should reference A."
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_agents_md.py::TestRenderDocumentStandards -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `uv run python -m pytest tests/test_agents_md.py -v`
Expected: All tests PASS. Existing tests should still pass since they assert
on content that hasn't changed (markers, areas, preferences, metadata format).

**Step 6: Commit**

```bash
git add wos/agents_md.py tests/test_agents_md.py
git commit -m "feat: add Document Standards subsection to AGENTS.md render"
```

---

### Task 2: Create `skills/init-wos/SKILL.md`

**Files:**
- Create: `skills/init-wos/SKILL.md`

**Step 1: Create the skill directory and file**

```bash
mkdir -p skills/init-wos
```

Write `skills/init-wos/SKILL.md`:

```markdown
---
name: init-wos
description: >
  Initialize or update WOS project context. Use when starting a new project
  with WOS, or re-run to verify and repair an existing setup. Idempotent —
  safe to run multiple times.
argument-hint: ""
user-invocable: true
references:
  - ../_shared/references/preflight.md
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
format, document standards, and any existing preferences. The markers enable
automated updates — never place WOS-managed content outside them.

If markers already exist, the section is replaced with the latest version
(picking up any new standards or areas).

### 5. Report

Report what was done:

- **Created:** list any directories or files that were created
- **Updated:** note if AGENTS.md WOS section was refreshed
- **Already present:** note anything that was already in place

If everything was already set up, confirm: "WOS is up to date. No changes needed."
```

**Step 2: Verify the skill file is valid**

Read back the file and confirm frontmatter has `name`, `description`,
`user-invocable: true`, and the preflight reference.

**Step 3: Commit**

```bash
git add skills/init-wos/SKILL.md
git commit -m "feat: create /init-wos skill"
```

---

### Task 3: Delete `skills/create/`

**Files:**
- Delete: `skills/create/SKILL.md`

**Step 1: Remove the directory**

```bash
rm -rf skills/create/
```

**Step 2: Verify it's gone**

```bash
ls skills/create/ 2>&1
```
Expected: "No such file or directory"

**Step 3: Commit**

```bash
git add -A skills/create/
git commit -m "chore: remove /create skill (replaced by /init-wos)"
```

---

### Task 4: Deduplicate convention guidance from `/distill`

**Files:**
- Modify: `skills/distill/SKILL.md:46-73`

**Step 1: Edit the Generate section**

In `skills/distill/SKILL.md`, replace the Generate section (### 4. Generate,
lines 46-73) with a simplified version. Keep the frontmatter example and
cross-referencing guidance (domain-specific to distillation). Replace the
lost-in-the-middle, word count, and bidirectional linking paragraphs with
one-liners.

Replace lines 68-73 (the lost-in-the-middle convention block and word count
report) with:

```markdown
2. Follow the document standards in AGENTS.md for structure, frontmatter,
   and word count guidance.
```

The full Generate section becomes:

```markdown
### 4. Generate

For each approved finding:

1. Write a context file with frontmatter:
   ```yaml
   ---
   name: [Concise title]
   description: [One-sentence summary]
   type: reference
   sources:
     - [Carry forward relevant URLs from research]
   related:
     - [Path to source research artifact]
     - [Path to other context file from this batch]
     - [Path to existing context file in the same area]
   ---
   ```

   Every distilled file should link to at least one sibling context file in
   `related:`, not just the source research document. When distilling a batch,
   include cross-references between thematically adjacent files.

2. Follow the document standards in AGENTS.md for structure, frontmatter,
   and word count guidance.
```

**Step 2: Verify the edit**

Read back the file. Confirm the lost-in-the-middle block (Top/Middle/Bottom),
word count report line, and "200-800 word" reference are gone from the Generate
section. The Key Constraints section at the bottom still mentions word count
advisory — leave it (it's about the distillation-specific constraint, not the
general convention).

**Step 3: Commit**

```bash
git add skills/distill/SKILL.md
git commit -m "refactor: replace duplicated conventions in /distill with AGENTS.md reference"
```

---

### Task 5: Deduplicate convention guidance from `/research`

**Files:**
- Modify: `skills/research/SKILL.md:106-115`

**Step 1: Replace the Document Structure Convention section**

In `skills/research/SKILL.md`, replace lines 106-115 (the entire
"## Document Structure Convention" section) with:

```markdown
## Document Standards

Follow the document standards in AGENTS.md for structure and frontmatter.
```

**Step 2: Verify the edit**

Read back the file. Confirm the old "LLMs lose attention in the middle"
paragraph is gone. Everything else (Mode Detection, Workflow, Phase Gates,
Common Deviations, Output Document Format, Key Rules) is unchanged.

**Step 3: Commit**

```bash
git add skills/research/SKILL.md
git commit -m "refactor: replace duplicated conventions in /research with AGENTS.md reference"
```

---

### Task 6: Update `/audit` references

**Files:**
- Modify: `skills/audit/SKILL.md:114-116,145`

**Step 1: Replace `/wos:create` references**

Three replacements in `skills/audit/SKILL.md`:

- Line 114: `Offer to run `/wos:create` to` → `Offer to run `/init-wos` to`
- Line 116: `Offer to run `/wos:create` to add` → `Offer to run `/init-wos` to add`
- Line 145: `Use `/wos:create` to create missing documents` → `Use `/init-wos` to initialize missing project structure`

**Step 2: Verify the edit**

Run: `grep -n "create" skills/audit/SKILL.md`
Expected: No remaining references to `/wos:create` or `/create`

**Step 3: Commit**

```bash
git add skills/audit/SKILL.md
git commit -m "refactor: update /audit references from /create to /init-wos"
```

---

### Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:88-100`

**Step 1: Update the skills table**

In `CLAUDE.md`:

- Line 88: Change `9 skills:` to `9 skills:` (count stays the same — we
  replaced one skill, not added/removed)
- Line 92: Replace:
  ```
  | `/wos:create` | Create project context, areas, or documents |
  ```
  with:
  ```
  | `/wos:init-wos` | Initialize or update WOS project context |
  ```
- Line 88: Update the example from `/wos:create` to `/wos:init-wos`:
  ```
  Prefix: `/wos:` (e.g., `/wos:init-wos`, `/wos:audit`). 9 skills:
  ```

**Step 2: Verify the edit**

Run: `grep -n "create" CLAUDE.md`
Expected: No remaining references to `/wos:create`

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md skills table for /init-wos"
```

---

### Task 8: Run full test suite and audit

**Step 1: Run all tests**

Run: `uv run python -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Verify no references to old skill remain**

Run: `grep -r "wos:create\|/create" skills/ CLAUDE.md tests/ --include="*.md" --include="*.py" | grep -v __pycache__`
Expected: No results (or only references in the design/plan docs which are fine)

**Step 3: Commit if any fixups needed**

If any stray references were found and fixed, commit them.

---

## Branch / PR

- Branch: `feat/init-wos`
- PR: TBD — create after all tasks complete
