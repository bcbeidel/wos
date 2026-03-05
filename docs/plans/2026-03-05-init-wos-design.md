---
name: "Replace /create with /init-wos"
description: "Simplify the create skill into a focused initialization skill and move document standards into AGENTS.md"
type: plan
related:
  - docs/plans/2026-02-27-architecture-reference.md
  - docs/plans/2026-02-22-simplification-design.md
---

# Replace `/create` with `/init-wos`

## Summary

The `/wos:create` skill currently does three jobs: initialize a project, add
areas, and create documents. The "create document" job overlaps heavily with
`/distill` and `/research`, and the "add area" job is trivial (`mkdir` +
reindex). This plan simplifies `/create` into `/init-wos` — a focused,
idempotent bootstrap skill — and moves document standards into AGENTS.md as
the single source of truth.

## Motivation

- **Document conventions are duplicated** across `/create`, `/distill`, and
  `/research` (lost-in-the-middle, word count, related linking)
- **"Create document" is redundant** — research creates research docs, distill
  creates context docs, and both already know the conventions
- **"Add area" is trivial** — it's `mkdir` + `reindex`, doesn't need a skill
- **AGENTS.md is under-leveraged** — Claude reads it every session, but it only
  has a one-line mention of document structure

## Design Decisions

- **Idempotent behavior:** `/init-wos` is safe to re-run. On a fresh repo it
  scaffolds everything. On an initialized repo it verifies and repairs gaps
  (re-renders AGENTS.md WOS section to pick up latest standards).
- **Approach C — expand AGENTS.md + deduplicate skills:** Document standards
  live in `render_wos_section()` in `agents_md.py`. Skills that write documents
  get a one-liner pointing to AGENTS.md instead of duplicating conventions.
- **Naming:** `init-wos` avoids collision with Claude Code's built-in `/init`
  command and reads clearly in the slash command UI.

## Changes

### 1. Delete `skills/create/`

- [ ] Remove `skills/create/SKILL.md`

### 2. Create `skills/init-wos/SKILL.md`

- [ ] New skill with `name: init-wos`
- [ ] Single workflow (no routing):
  - Create `docs/context/`, `docs/research/`, `docs/plans/` if missing
  - Create `_index.md` in each via `reindex.py`
  - Create or update AGENTS.md WOS section (between markers)
  - Report what was created vs. what already existed
- [ ] Reference `preflight.md`

### 3. Expand `render_wos_section()` in `wos/agents_md.py`

- [ ] Add "Document Standards" subsection covering:
  - Structure: key insights first, detail middle, takeaways bottom
  - Frontmatter: required/optional fields
  - Conventions: 200-800 word target, bidirectional linking, one concept per file
- [ ] Update tests for new AGENTS.md output

### 4. Deduplicate convention guidance from skills

- [ ] `/distill` SKILL.md: Replace lost-in-the-middle, word count, and related
  linking guidance in Generate section with one-liner:
  "Follow the document standards in AGENTS.md for structure, frontmatter, and
  word count guidance."
- [ ] `/research` SKILL.md: Replace "Document Structure Convention" section
  (lines 107-115) with one-liner:
  "Follow the document standards in AGENTS.md for structure and frontmatter."

### 5. Update references to `/wos:create`

- [ ] `/audit` SKILL.md: Change cleanup action references from `/wos:create`
  to `/init-wos`
- [ ] CLAUDE.md: Replace `create` row in skills table with `init-wos`, update
  description and skill count

### 6. Update tests

- [ ] Update any tests that reference the create skill or assert on AGENTS.md
  rendered output (new Document Standards subsection will change expected output)

## Not Changed

- `skills/distill/references/distillation-guidelines.md` — domain-specific
  (splitting heuristics, confidence mapping), stays as-is
- All Python modules other than `wos/agents_md.py`
- `/research` skill — all SIFT, phase gates, claim verification guidance stays

## Branch / PR

- Branch: `feat/init-wos`
- PR: TBD
