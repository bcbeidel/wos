---
name: Lifecycle Clarity — Designs Directory and Validate-Work Rename
description: Separate design specs from plans into docs/designs/ and rename validate-plan to validate-work
type: plan
status: completed
related:
  - docs/plans/2026-03-11-lifecycle-clarity.md
---

# Goal

Make the design → plan lifecycle explicit by (1) giving design specs their own
directory (`docs/designs/`) instead of co-locating them in `docs/plans/`, and
(2) renaming `wos:validate-plan` to `wos:validate-work` so the skill name
reflects that it validates completed work, not the plan document itself.

Closes #173, #177.

# Scope

**Must have:**
- `docs/designs/` as the output location for `wos:brainstorm`
- `wos:init` creates `docs/designs/`
- `reindex.py` indexes `docs/designs/` (already works — it walks all `docs/` subdirs)
- AGENTS.md navigation includes `docs/designs/_index.md`
- `skills/validate-plan/` → `skills/validate-work/` with updated metadata
- All cross-references in active skills and shared references updated consistently
- OVERVIEW.md reflects both changes

**Won't have:**
- Retroactively moving existing design files from `docs/plans/`
- Changing plan format, validate-work behavior, or document.py type system
- Adding `type: design` validation in document.py (not needed — designs already use this type)

# Approach

Two independent chunks. The designs directory change touches brainstorm,
write-plan, init, agents_md.py, and shared references. The rename touches
validate-plan, execute-plan, and OVERVIEW.md. Both touch OVERVIEW.md but
different sections.

Historical documents in `docs/plans/` that reference `validate-plan` or
contain `docs/plans/...-design.md` paths are left as-is — they are records
of past work, not live instructions.

# File Changes

**Create:**
- (none — `docs/designs/` is created by `wos:init`, not committed empty)

**Modify:**
- `skills/brainstorm/SKILL.md` — save path `docs/plans/` → `docs/designs/` (2 locations)
- `skills/write-plan/SKILL.md` — design doc `related:` example path
- `skills/_shared/references/plan-format.md` — design doc `related:` example path
- `skills/init/SKILL.md` — add `designs/` to directory list
- `wos/agents_md.py` — add `docs/designs/_index.md` to navigation links
- `skills/validate-work/SKILL.md` — rename + update name, description, announce text (moved from `skills/validate-plan/`)
- `skills/execute-plan/SKILL.md` — `wos:validate-plan` → `wos:validate-work` (2 references)
- `OVERVIEW.md` — validate-plan → validate-work in flowchart, table, and prose; add `docs/designs/` to infrastructure description

**Move:**
- `skills/validate-plan/` → `skills/validate-work/` (directory rename, preserves references/)

**Delete:**
- `skills/validate-plan/` (after move)

# Tasks

## Chunk 1: docs/designs/ directory

- [x] Task 1: Update brainstorm skill save path <!-- sha:415e5b1 -->
  - In `skills/brainstorm/SKILL.md`, change `docs/plans/YYYY-MM-DD-<name>-design.md` to `docs/designs/YYYY-MM-DD-<name>-design.md` (lines 59 and 135)
  - Verify: `grep -c "docs/designs/" skills/brainstorm/SKILL.md` returns 2; `grep -c "docs/plans/.*design" skills/brainstorm/SKILL.md` returns 0

- [x] Task 2: Update write-plan and plan-format design doc references <!-- sha:d73dd25 -->
  - In `skills/write-plan/SKILL.md`, change the `related:` example from `docs/plans/YYYY-MM-DD-<name>-design.md` to `docs/designs/YYYY-MM-DD-<name>-design.md`
  - In `skills/_shared/references/plan-format.md`, change the `related:` example from `docs/plans/YYYY-MM-DD-<topic>-design.md` to `docs/designs/YYYY-MM-DD-<topic>-design.md`
  - Verify: `grep "docs/plans/.*design" skills/write-plan/SKILL.md skills/_shared/references/plan-format.md` returns no matches

- [x] Task 3: Update init skill to create docs/designs/ <!-- sha:ee64839 -->
  - In `skills/init/SKILL.md`, add `designs/` to the directory tree in Step 1 (check list) and Step 2 (create list)
  - Verify: `grep -c "designs" skills/init/SKILL.md` returns at least 2

- [x] Task 4: Update agents_md.py navigation to include docs/designs/ <!-- sha:e4d4ec6 -->
  - In `wos/agents_md.py`, add `- docs/designs/_index.md -- designs` line after the plans line in `render_wos_section()`
  - Verify: `uv run python -m pytest tests/ -v -k agents` passes

## Chunk 2: validate-plan → validate-work rename

- [x] Task 5: Move skill directory and update SKILL.md metadata <!-- sha:da15a23 -->
  - `git mv skills/validate-plan skills/validate-work`
  - In `skills/validate-work/SKILL.md`: change `name: validate-plan` → `name: validate-work`, update description to say "validate the work" / "verify the work" instead of "validate the plan" / "verify the plan", update announce text, update title
  - Verify: `test -d skills/validate-work && ! test -d skills/validate-plan`

- [x] Task 6: Update execute-plan cross-references <!-- sha:a8cb09b -->
  - In `skills/execute-plan/SKILL.md`, change `wos:validate-plan` to `wos:validate-work` (2 occurrences, lines 97 and 100)
  - Verify: `grep -c "validate-work" skills/execute-plan/SKILL.md` returns 2; `grep -c "validate-plan" skills/execute-plan/SKILL.md` returns 0

- [x] Task 7: Update OVERVIEW.md <!-- sha:1c68d6f -->
  - In `OVERVIEW.md` flowchart: `validateplan["/wos:validate-plan"]` → `validatework["/wos:validate-work"]`; update node references (`validateplan` → `validatework`)
  - In prose: "Validate Plan" → "Validate Work" in delivery layer description
  - In skills table: `/wos:validate-plan` → `/wos:validate-work`, update purpose text
  - Add `docs/designs/` to infrastructure layer description alongside existing directories
  - Verify: `grep -c "validate-plan" OVERVIEW.md` returns 0; `grep -c "validate-work" OVERVIEW.md` returns at least 3; `grep -c "designs" OVERVIEW.md` returns at least 1

# Validation

1. `uv run python -m pytest tests/ -v` — all tests pass
2. `grep -r "validate-plan" skills/ --include="*.md"` returns no matches in active skill files
3. `grep "docs/plans/.*design" skills/brainstorm/SKILL.md skills/write-plan/SKILL.md skills/_shared/references/plan-format.md` returns no matches
4. `skills/validate-work/SKILL.md` exists and contains `name: validate-work`
5. `skills/validate-plan/` directory does not exist
6. `grep "designs" wos/agents_md.py` returns a match (navigation link present)
7. `grep "designs" skills/init/SKILL.md` returns matches (directory in init workflow)
