---
name: Flexible Document Layout
description: Decouple WOS from fixed directory hierarchies — discover documents by frontmatter, type by suffix/metadata, navigate by actual structure
type: plan
status: completed
related:
  - docs/designs/2026-03-13-flexible-layout.design.md
---

# Flexible Document Layout

**Goal:** Users can place WOS documents anywhere in their project tree. WOS
discovers documents by walking the tree and checking for frontmatter, validates
by document type (not path), and generates navigation from actual structure.
Existing `docs/` layouts continue to work unchanged.

**Scope:**

Must have:
- Tree walker with `.gitignore` filtering and `.git/` exclusion
- Document detection by frontmatter presence (`name` + `description`)
- Type-based validation (no path-based filtering)
- Discovery-based AGENTS.md navigation generation
- Layout pattern selection during `/wos:init-wos`
- Layout hint stored in AGENTS.md (`<!-- wos:layout: ... -->`)
- Assessment scripts (`assess_research`, `assess_plan`) use discovery
- Skill instructions updated to suggest (not hardcode) save locations

Won't have:
- Separate config file (`.wos.yaml`, `pyproject.toml` entries)
- Pattern enforcement (hint is advisory only)
- Migration tooling for existing projects
- Multi-root config
- Nested `.gitignore` support (root `.gitignore` only for v1)

**Approach:** Create a `wos/discovery.py` module that walks the project tree
(respecting `.gitignore`), identifies managed documents by frontmatter, and
returns typed `Document` references. Update validators, agents_md, scripts,
and assessment modules to use discovery instead of hardcoded `docs/` walks.
Update skill instructions to read the layout hint and suggest save paths.
Rename `/wos:init` to `/wos:init-wos` and add pattern selection.

**File Changes:**
- Create: `wos/discovery.py`
- Create: `tests/test_discovery.py`
- Modify: `wos/validators.py`
- Modify: `wos/agents_md.py`
- Modify: `scripts/audit.py`
- Modify: `scripts/reindex.py`
- Modify: `wos/research/assess_research.py`
- Modify: `wos/plan/assess_plan.py`
- Modify: `tests/test_validators.py` (if exists, or update existing tests)
- Modify: `tests/test_agents_md.py` (if exists)
- Modify: `skills/init/SKILL.md` (rename to `skills/init-wos/SKILL.md`)
- Modify: `skills/brainstorm/SKILL.md`
- Modify: `skills/write-plan/SKILL.md`
- Modify: `skills/research/SKILL.md`
- Modify: `skills/distill/SKILL.md`

**Branch:** `feat/flexible-layout` (active)
**PR:** TBD

---

## Chunk 1: Discovery Foundation

### Task 1: Create `wos/discovery.py` — tree walker with gitignore support

**Files:**
- Create: `wos/discovery.py`

- [x] Implement `.gitignore` pattern matching (stdlib only). Support: glob patterns (`*.pyc`, `build/`), negation (`!important.md`), directory markers (trailing `/`), comments (`#`), blank lines. Use `fnmatch` from stdlib for glob matching. <!-- sha:50c6684 -->
- [x] Implement `load_gitignore(root: Path) -> list` that reads `root/.gitignore` and returns parsed patterns. Returns empty list if no `.gitignore` exists. <!-- sha:50c6684 -->
- [x] Implement `is_ignored(path: Path, root: Path, patterns: list) -> bool` that checks if a path matches any gitignore pattern. Always returns `True` for `.git/`. <!-- sha:50c6684 -->
- [x] Implement `discover_documents(root: Path) -> list[Document]` that walks the tree, skips ignored paths, reads each `.md` file, and returns parsed `Document` instances for files with valid frontmatter (`name` + `description`). Skips `_index.md` files. <!-- sha:50c6684 -->
- [x] Implement `discover_document_dirs(root: Path) -> list[Path]` that returns directories containing at least one managed document (for index generation). <!-- sha:50c6684 -->
- [x] Verify: `python -c "from wos.discovery import discover_documents; print('OK')"` <!-- sha:50c6684 -->
- [x] Commit <!-- sha:50c6684 -->

---

### Task 2: Tests for discovery module

**Files:**
- Create: `tests/test_discovery.py`

- [x] Test gitignore parsing: basic globs (`*.pyc`), directory patterns (`build/`), negation (`!keep.md`), comments, blank lines. <!-- sha:0ad9234 -->
- [x] Test `is_ignored`: `.git/` always ignored, patterns match correctly, negation overrides. <!-- sha:0ad9234 -->
- [x] Test `discover_documents`: creates a `tmp_path` tree with mixed `.md` files (some with frontmatter, some without), a `.gitignore`, and verifies only valid frontmatter files are returned. Verifies `_index.md` is excluded. <!-- sha:0ad9234 -->
- [x] Test `discover_document_dirs`: returns correct set of directories. <!-- sha:0ad9234 -->
- [x] Test type resolution: suffix-based type, frontmatter type, frontmatter-wins-on-conflict. <!-- sha:0ad9234 -->
- [x] Test empty project (no `.md` files, no `.gitignore`). <!-- sha:0ad9234 -->
- [x] Verify: `python -m pytest tests/test_discovery.py -v` <!-- sha:0ad9234 -->
- [x] Commit <!-- sha:0ad9234 -->

---

## Chunk 2: Validator & Navigation Updates

### Task 3: Update `wos/validators.py` — type-based validation rules

**Files:**
- Modify: `wos/validators.py`

**Depends on:** Task 1

- [x] `check_frontmatter()`: Remove `context_path` parameter. Change the "context files should have related fields" check to use `doc.type == "context"` instead of `doc.path.startswith(context_path + "/")`. <!-- sha:c3d6be3 -->
- [x] `check_content()`: Remove `context_path` parameter. Change word-count filtering to use `doc.type == "context"` instead of path prefix check. <!-- sha:c3d6be3 -->
- [x] `validate_file()`: Update call sites for removed `context_path` parameter. <!-- sha:c3d6be3 -->
- [x] `validate_project()`: Replace hardcoded `docs_dir = root / "docs"` walk with `discover_documents(root)`. Iterate discovered documents instead of walking `docs/` subdirectories. Use `discover_document_dirs(root)` for index sync checks. <!-- sha:c3d6be3 -->
- [x] Verify: `python -m pytest tests/ -v` — existing tests pass (may need updates in Task 5). <!-- sha:c3d6be3 -->
- [x] Commit <!-- sha:c3d6be3 -->

---

### Task 4: Update `wos/agents_md.py` — discovery-based navigation

**Files:**
- Modify: `wos/agents_md.py`

**Depends on:** Task 1

- [x] `discover_areas()`: Replace hardcoded `docs/context/` scan with `discover_document_dirs(root)`. Return all directories containing managed documents as navigable areas (not just `docs/context/` subdirectories). <!-- sha:e4fb28b -->
- [x] `render_wos_section()`: Replace hardcoded navigation lines (`docs/context/_index.md`, `docs/plans/_index.md`, etc.) with dynamically generated list from `areas`. Each area gets its `_index.md` link. <!-- sha:e4fb28b -->
- [x] Add `read_layout_hint(content: str) -> Optional[str]` — extract layout pattern from `<!-- wos:layout: ... -->` comment in AGENTS.md WOS section. <!-- sha:e4fb28b -->
- [x] Add `write_layout_hint(layout: str) -> str` — return the comment marker string for a given layout pattern. <!-- sha:e4fb28b -->
- [x] Update `render_wos_section()` to accept optional `layout` parameter and include the hint comment. <!-- sha:e4fb28b -->
- [x] Verify: `python -c "from wos.agents_md import read_layout_hint; print('OK')"` <!-- sha:e4fb28b -->
- [x] Commit <!-- sha:e4fb28b -->

---

### Task 5: Update tests for validators and agents_md

**Files:**
- Modify: `tests/test_validators.py` (if exists)
- Modify: `tests/test_agents_md.py` (if exists)

**Depends on:** Tasks 3, 4

- [x] Update validator tests: remove any path-based assumptions. Test that context-type docs get word-count checks regardless of location. Test that research-type docs require sources regardless of location. <!-- sha:e4fb28b -->
- [x] Update agents_md tests: test `discover_areas()` returns directories from arbitrary locations. Test `read_layout_hint()` and `write_layout_hint()`. Test `render_wos_section()` generates dynamic navigation. <!-- sha:e4fb28b -->
- [x] Verify: `python -m pytest tests/ -v` <!-- sha:e4fb28b -->
- [x] Commit <!-- sha:e4fb28b -->

---

## Chunk 3: Script & Assessment Updates

### Task 6: Update `scripts/audit.py` and `scripts/reindex.py`

**Files:**
- Modify: `scripts/audit.py`
- Modify: `scripts/reindex.py`

**Depends on:** Tasks 3, 4

- [x] `audit.py`: `validate_project()` already updated in Task 3 — verify the script works end-to-end with documents in non-standard locations. <!-- sha:196bb5d -->
- [x] `reindex.py`: Replace `docs_dir = root / "docs"` walk with `discover_document_dirs(root)`. Generate `_index.md` for each discovered directory. Remove hard error when `docs/` doesn't exist. <!-- sha:196bb5d -->
- [x] `reindex.py`: Update `_update_agents_md_areas()` — `discover_areas()` already updated in Task 4. <!-- sha:196bb5d -->
- [x] Verify: create a temp project with files outside `docs/`, run `python scripts/audit.py --root <tmp>` and `python scripts/reindex.py --root <tmp>`. <!-- sha:196bb5d -->
- [x] Commit <!-- sha:196bb5d -->

---

### Task 7: Update assessment modules to use discovery

**Files:**
- Modify: `wos/research/assess_research.py`
- Modify: `wos/plan/assess_plan.py`

**Depends on:** Task 1

- [x] `assess_research.py` `scan_directory()`: Replace directory-based scan with discovery-based scan. Find all `type: research` documents using `discover_documents()`, filtered by type. Keep `--subdir` parameter as optional scope filter (backwards compat), but default to full-tree discovery when not specified. <!-- sha:ab117d6 -->
- [x] `assess_plan.py` `scan_plans()`: Same approach — use discovery to find `type: plan` documents with `status: executing`. Keep `--subdir` as optional scope filter. <!-- sha:ab117d6 -->
- [x] Verify: `python -m pytest tests/ -v` <!-- sha:ab117d6 -->
- [x] Commit <!-- sha:ab117d6 -->

---

## Chunk 4: Skill Updates

### Task 8: Rename init to init-wos, add pattern selection

**Files:**
- Create: `skills/init-wos/SKILL.md` (move from `skills/init/SKILL.md`)
- Delete: `skills/init/SKILL.md`

- [x] Rename the `skills/init/` directory to `skills/init-wos/`. Move all contents. <!-- sha:a7590ae -->
- [x] Update SKILL.md: add a pattern selection step to the setup flow. After creating AGENTS.md/CLAUDE.md, present the four layout patterns (separated, co-located, flat, none) and ask user to choose. <!-- sha:a7590ae -->
- [x] Update SKILL.md: based on selection, create appropriate initial directory structure (or none). Write layout hint to AGENTS.md via `<!-- wos:layout: <choice> -->`. <!-- sha:a7590ae -->
- [x] Update SKILL.md: change all references from `/wos:init` to `/wos:init-wos`. <!-- sha:a7590ae -->
- [x] Update any other skills or docs that reference `/wos:init` to use `/wos:init-wos`. <!-- sha:a7590ae -->
- [x] Verify: `ls skills/init-wos/SKILL.md` exists, `ls skills/init/` does not. <!-- sha:a7590ae -->
- [x] Commit <!-- sha:a7590ae -->

---

### Task 9: Update output-producing skills to use layout hint

**Files:**
- Modify: `skills/brainstorm/SKILL.md`
- Modify: `skills/write-plan/SKILL.md`
- Modify: `skills/research/SKILL.md`
- Modify: `skills/distill/SKILL.md`

**Depends on:** Task 4 (layout hint functions)

- [x] `brainstorm/SKILL.md`: Replace hardcoded `docs/designs/YYYY-MM-DD-<name>.design.md` with instruction to read the layout hint from AGENTS.md and suggest a save path accordingly. For `separated` → `docs/designs/`, for `co-located` → same directory as related docs, for `flat` → `docs/`, for `none` → ask user. Always allow user override. <!-- sha:298a523 -->
- [x] `write-plan/SKILL.md`: Same pattern — replace hardcoded `docs/plans/` with layout-aware suggestion. <!-- sha:298a523 -->
- [x] `research/SKILL.md`: Same pattern — replace hardcoded `docs/research/` with layout-aware suggestion. <!-- sha:298a523 -->
- [x] `distill/SKILL.md`: Same pattern — replace hardcoded `docs/context/` with layout-aware suggestion. <!-- sha:298a523 -->
- [x] Update each skill to check for existing related documents and suggest co-location when relevant. <!-- sha:298a523 -->
- [x] Verify: read each modified SKILL.md and confirm no hardcoded `docs/<type>/` output paths remain. <!-- sha:298a523 -->
- [x] Commit <!-- sha:298a523 -->

---

## Validation

- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] `ruff check wos/ tests/ scripts/` — no lint errors (if ruff available)
- [ ] Create a temp project with `separated` layout, run audit — works as before
- [ ] Create a temp project with `flat` layout (all files in `docs/`), run audit — all documents discovered and validated by type
- [ ] Create a temp project with `co-located` layout (`docs/auth/` containing `.plan.md`, `.research.md`, `.context.md`), run audit — all discovered and typed correctly
- [ ] Create a temp project with `none` layout (files in project root and arbitrary dirs), run audit — all discovered
- [ ] Run reindex on each layout — `_index.md` generated only in directories with managed documents
- [ ] Verify `.gitignore` patterns are respected — files in ignored directories are not discovered
- [ ] Verify `.git/` is never walked
- [ ] Verify existing WOS project (`docs/` structure) works with zero changes after upgrade
