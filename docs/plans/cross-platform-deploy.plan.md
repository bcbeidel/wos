---
name: Cross-Platform Skill Deployment
description: Deploy script that exports WOS skills to .agents/ for Copilot and other Agent Skills-compatible copilots
type: plan
status: completed
created_at: 2026-03-13
related:
  - docs/designs/cross-platform-deploy-design.md
---

# Cross-Platform Skill Deployment

**Goal:** WOS skills can be deployed into any project's `.agents/` directory
and used by GitHub Copilot (and other Agent Skills-compatible copilots)
without requiring `uv` or Claude Code. This enables WOS adoption in client
ecosystems where only native Python is available.

**Scope:**

Must have:
- `scripts/deploy.py` — stdlib-only export script
- Copies `skills/`, `scripts/`, `wos/` into `<target>/.agents/`
- Rewrites `uv run` → `python` in all deployed `.md` files
- Strips `preflight.md` from SKILL.md `references:` frontmatter
- Excludes `check_runtime.py` (uv canary, only external dep) and `preflight.md`
- `--target PATH` (required) and `--dry-run` flags
- Idempotent (safe to re-run)
- Tests for copy, rewrite, and exclusion logic

Won't have:
- Per-platform optimization (Cursor `.mdc` generation, etc.)
- Modification of source repo files
- Modification of Python scripts (root detection already works via `__file__` fallback)
- Plugin root env var changes (existing `CLAUDE_PLUGIN_ROOT` → `__file__` fallback is sufficient)
- Version management or update detection in deployed targets

**Approach:** Single stdlib-only script that walks the source tree, copies
files preserving directory structure, and applies text transforms to `.md`
files during copy. Markdown rewriting uses simple string replacement for
`uv run` → `python` and regex for stripping preflight references from
YAML frontmatter. The deployed directory structure mirrors the source repo
structure (skills/, scripts/, wos/ as siblings), preserving the `__file__`
parent-chain root detection that all scripts already use.

**File Changes:**
- Create: `scripts/deploy.py`
- Create: `tests/test_deploy.py`

**Branch:** `cross-platform-deploy`
**PR:** TBD

---

### Task 1: Create deploy.py with file copy and exclusions

**Files:**
- Create: `scripts/deploy.py`

- [x] Create `scripts/deploy.py` with PEP 723 metadata (stdlib-only, Python >=3.9) <!-- sha:e37626e -->
- [x] Add argparse CLI: `--target PATH` (required), `--dry-run` <!-- sha:e37626e -->
- [x] Implement source discovery: walk `skills/`, `scripts/`, `wos/` from plugin root <!-- sha:e37626e -->
- [x] Implement exclusion list: skip `check_runtime.py`, `preflight.md`, `__pycache__/`, `.pyc` <!-- sha:e37626e -->
- [x] Implement copy logic: replicate directory structure under `<target>/.agents/` <!-- sha:e37626e -->
- [x] Verify: `python scripts/deploy.py --target /tmp/test-deploy --dry-run` lists files without writing <!-- sha:e37626e -->
- [x] Verify: `python scripts/deploy.py --target /tmp/test-deploy` creates `.agents/` structure with correct files <!-- sha:e37626e -->
- [x] Verify: `ls /tmp/test-deploy/.agents/wos/__init__.py` exists; `ls /tmp/test-deploy/.agents/scripts/audit.py` exists; `ls /tmp/test-deploy/.agents/skills/audit/SKILL.md` exists <!-- sha:e37626e -->
- [x] Verify: `find /tmp/test-deploy -name check_runtime.py` returns nothing; `find /tmp/test-deploy -name preflight.md` returns nothing <!-- sha:e37626e -->
- [x] Commit <!-- sha:e37626e -->

### Task 2: Add markdown transforms during copy

**Files:**
- Modify: `scripts/deploy.py` (add rewrite logic)

**Depends on:** Task 1

- [x] Implement `uv run` → `python` replacement for all `.md` files during copy <!-- sha:e37626e -->
- [x] Implement preflight reference stripping from SKILL.md frontmatter (remove `- ../_shared/references/preflight.md` lines) <!-- sha:e37626e -->
- [x] Handle preflight instruction blocks in SKILL.md bodies (references to "follow the preflight check" etc.) <!-- sha:e37626e -->
- [x] Verify: `grep -r "uv run" /tmp/test-deploy/.agents/` returns no matches in .md files <!-- sha:e37626e -->
- [x] Verify: `grep -r "preflight" /tmp/test-deploy/.agents/skills/audit/SKILL.md` returns no matches <!-- sha:e37626e -->
- [x] Verify: deployed SKILL.md files still have valid YAML frontmatter (name, description present) <!-- sha:e37626e -->
- [x] Commit <!-- sha:e37626e -->

### Task 3: Write tests

**Files:**
- Create: `tests/test_deploy.py`

**Depends on:** Task 2

- [x] Test file discovery finds expected source files <!-- sha:856c101 -->
- [x] Test exclusion: `check_runtime.py` and `preflight.md` not in output <!-- sha:856c101 -->
- [x] Test `uv run` → `python` rewriting in markdown content <!-- sha:856c101 -->
- [x] Test preflight reference line removed from SKILL.md frontmatter YAML <!-- sha:856c101 -->
- [x] Test copy preserves directory structure (skills/, scripts/, wos/ as siblings under .agents/) <!-- sha:856c101 -->
- [x] Test idempotency: running deploy twice produces same output <!-- sha:856c101 -->
- [x] Test `--dry-run` writes nothing to disk <!-- sha:856c101 -->
- [x] Verify: `uv run python -m pytest tests/test_deploy.py -v` — all pass (20/20) <!-- sha:856c101 -->
- [x] Commit <!-- sha:856c101 -->

### Task 4: End-to-end validation

**Depends on:** Task 3

- [x] Run full test suite: `uv run python -m pytest tests/ -v` — 337 passed, 0 failures <!-- sha:856c101 -->
- [x] Run audit: skipped (no new source files requiring audit)
- [x] Deploy to temp directory: `python scripts/deploy.py --target /tmp/e2e-test` — 82 files deployed
- [x] Verify skill count: 13 source skills = 13 deployed skills
- [x] Verify script importability: `from wos.document import parse_document` — ok
- [x] Verify a deployed script runs: `python .agents/scripts/audit.py --root .` — runs clean, expected project warnings only
- [x] No fixes needed

---

## Chunk 2: Remove uv Runtime Dependency

Remove `uv run` from all active skill instructions so source and deployed
forms are identical. Keep uv as optional dev tooling (pytest, ruff).

### Task 5: Rewrite skill instructions — uv run → python

**Files:**
- Modify: 8 SKILL.md files, 15 reference .md files under skills/

- [x] Replace `uv run` → `python` in all SKILL.md files <!-- sha:917c71b -->
- [x] Replace `uv run` → `python` in all reference .md files under skills/ <!-- sha:917c71b -->
- [x] Strip `preflight.md` from SKILL.md `references:` frontmatter (8 files) <!-- sha:917c71b -->
- [x] Remove preflight instruction lines from SKILL.md bodies <!-- sha:917c71b -->
- [x] Verify: `grep -r "uv run" skills/` — only preflight.md (to be deleted in Task 6) <!-- sha:917c71b -->
- [x] Verify: `grep -r "preflight" skills/*/SKILL.md` — no matches <!-- sha:917c71b -->
- [x] Commit <!-- sha:917c71b -->

### Task 6: Delete preflight infrastructure and update project docs

**Files:**
- Delete: `scripts/check_runtime.py`
- Delete: `skills/_shared/references/preflight.md`
- Delete: `tests/test_check_runtime.py`
- Modify: `CLAUDE.md` (update invocation convention)
- Modify: `README.md` (update usage examples)

**Depends on:** Task 5

- [x] Delete `scripts/check_runtime.py`, `skills/_shared/references/preflight.md`, `tests/test_check_runtime.py` <!-- sha:5f8ac2f -->
- [x] Update CLAUDE.md: change "uv run is the universal pattern" convention to `python` <!-- sha:5f8ac2f -->
- [x] Update README.md: replace `uv run` in usage examples <!-- sha:5f8ac2f -->
- [x] Update docs/context files if they reference `uv run` as convention — context files describe platform facts, not conventions; left as-is <!-- sha:5f8ac2f -->
- [x] Verify: `grep -r "check_runtime" --include="*.py" --include="*.md" .` — remaining refs in historical docs/plans + deploy.py/tests (Task 7) <!-- sha:5f8ac2f -->
- [x] Commit <!-- sha:5f8ac2f -->

### Task 7: Simplify deploy.py — remove transform logic

**Files:**
- Modify: `scripts/deploy.py` (remove transform_markdown, simplify)
- Modify: `tests/test_deploy.py` (remove transform tests, update expectations)

**Depends on:** Task 6

- [x] Remove `transform_markdown()` function from deploy.py <!-- sha:366c6b1 -->
- [x] Simplify `deploy()` — copy all files directly, no markdown transforms <!-- sha:366c6b1 -->
- [x] Keep exclusion of `__pycache__/` and `.pyc` files <!-- sha:366c6b1 -->
- [x] Remove `check_runtime.py` and `preflight.md` from exclusion list (files no longer exist) <!-- sha:366c6b1 -->
- [x] Update tests: remove TestTransformMarkdown class, simplify deploy assertions <!-- sha:366c6b1 -->
- [x] Verify: `uv run python -m pytest tests/test_deploy.py -v` — all pass (10/10) <!-- sha:366c6b1 -->
- [x] Commit <!-- sha:366c6b1 -->

### Task 8: Final validation

**Depends on:** Task 7

- [x] Run full test suite: `python -m pytest tests/ -v` — 324 passed, 0 failures <!-- sha:366c6b1 -->
- [x] Deploy to temp directory: `python scripts/deploy.py --target /tmp/final-test` — 82 files deployed
- [x] Verify source and deployed SKILL.md are identical: `diff` — no differences
- [x] Verify deployed script runs: `cd /tmp/final-test && python .agents/scripts/audit.py --root . --no-urls` — runs clean
- [x] No fixes needed

---

## Validation

- [x] `uv run python -m pytest tests/ -v` — 324 passed, 0 failures
- [x] `uv run scripts/audit.py --root .` — skipped (no new source content files)
- [x] `python scripts/deploy.py --target /tmp/final-test` — exits 0, 82 files
- [x] `grep -r "uv run" /tmp/final-test/.agents/` — no matches (source files cleaned)
- [x] `grep -r "preflight" /tmp/final-test/.agents/skills/*/SKILL.md` — no matches
- [x] `find /tmp/final-test/.agents -name check_runtime.py` — no matches (file deleted)
- [x] `cd /tmp/final-test && python .agents/scripts/audit.py --root .` — runs clean
