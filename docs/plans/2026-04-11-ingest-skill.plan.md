---
name: /wos:ingest Skill
description: Add skills/ingest/SKILL.md — universal source intake that updates 5–15 wiki pages per invocation with append-only semantics
type: plan
status: completed
branch: feat/ingest-skill
pr: ~
related:
  - docs/plans/2026-04-10-roadmap-v036-v039.plan.md
---

# /wos:ingest Skill

Add the `/wos:ingest` skill: a universal knowledge intake mechanism that
accepts any source (URL, file path, pasted text, research doc) and updates
wiki pages in a single invocation.

## Goal

Deliver `skills/ingest/SKILL.md` with the full ingest protocol: trigger
phrases, pre-ingest context reads, LLM ingest loop, append-only constraint,
contradiction flagging, post-ingest lint + reindex, and an opt-in high-rigor
path for research documents. This is the primary knowledge intake mechanism
for wiki-enabled projects, replacing the narrow `distill` workflow for
knowledge capture.

## Scope

**Must have:**
- `skills/ingest/SKILL.md` with all required sections
- Trigger phrase list matching the issue spec
- Pre-ingest: read `wiki/_index.md` and `wiki/SCHEMA.md`
- Ingest protocol: identify 5–15 affected pages (new + existing)
- Per-page: append-only content update, `type`/`confidence`/`sources`/`updated`/`related` frontmatter updates
- Contradiction flagging: `<!-- CONTRADICTION: ... -->` markers
- New page creation when no existing page covers the topic
- Post-ingest: `python scripts/lint.py --root <project-root> --no-urls` + `python scripts/reindex.py --root <project-root>`
- High-rigor opt-in path: when source is `.research.md`, offer SIFT verification before ingest (default: skip)
- Append-only constraint stated explicitly in SKILL.md

**Won't have:**
- Python implementation code (skill is LLM-only instructions)
- Automated test for skill behavior (skills are tested by invocation, not unit tests)
- Deletion or deprecation of `distill` (tracked separately for v0.37.0 reassessment)
- Changes to `wos/wiki.py` or `scripts/lint.py` (wiki schema infrastructure is Task 2, already merged)

## Approach

Single deliverable: `skills/ingest/SKILL.md`. Follow the structure of
existing skills (frontmatter + named sections). The skill instructs Claude
to execute the ingest protocol inline — no subagent dispatch needed given
the sequential nature of the operations.

Key design decisions from the issue:
- **Context-first:** Always read `wiki/_index.md` and `wiki/SCHEMA.md` before
  any edits. Without the schema, confidence values and type assignments are
  guesses.
- **Append-only is non-negotiable.** Stated as an explicit constraint, not a
  guideline. Existing prose is never removed or overwritten.
- **5–15 page target.** Prevents both under-ingestion (missing connections)
  and over-ingestion (polluting unrelated pages).
- **Post-ingest gates.** Lint and reindex run unconditionally after every
  ingest, with results reported to the user. Issues don't block ingest, but
  must be surfaced.

## File Changes

| File | Action | Notes |
|------|--------|-------|
| `skills/ingest/SKILL.md` | Create | Full skill definition per issue spec |

No other files changed. The skill directory name (`ingest`) matches the
trigger: `/wos:ingest`.

## Tasks

### Task 1 — Create `skills/ingest/SKILL.md`

Create the skill file with the following required content:

**Frontmatter:**
```yaml
---
name: ingest
description: >
  Ingest any source into wiki pages. Use when the user says "ingest this",
  "add to wiki", "process this source", "update wiki with", or provides a
  URL/file/pasted text for knowledge capture.
argument-hint: "[URL | file path | pasted content]"
user-invocable: true
---
```

**Required sections:**
1. `## Input Handling` — accept URL, file path, or pasted text; resolve to readable content before proceeding
2. `## Pre-Ingest` — read `wiki/_index.md` (page inventory) and `wiki/SCHEMA.md` (valid types and confidence values)
3. `## Ingest Protocol` — identify 5–15 affected pages; for each: append-only content update, assign `type`+`confidence`, update `sources`/`updated`/`related`, flag contradictions as `<!-- CONTRADICTION: ... -->`, create new pages for uncovered topics
4. `## Append-Only Constraint` — explicit statement that existing prose is never removed or overwritten
5. `## Post-Ingest` — run `python scripts/lint.py --root <project-root> --no-urls` and `python scripts/reindex.py --root <project-root>`; report new lint issues to user
6. `## High-Rigor Path` — when source is a `.research.md` file, offer opt-in SIFT verification before ingest; default is to skip SIFT

**Verification:**
```bash
# Required content present
grep -E "append-only|SCHEMA\.md|_index\.md|contradiction" skills/ingest/SKILL.md
# Expected: all four match (4 lines minimum)

# Skill passes lint quality checks
python scripts/lint.py --root .
# Expected: no failures for skills/ingest/SKILL.md
```

**Commit:** `feat: add /wos:ingest skill (closes #219)` <!-- sha:30c42b5 -->

---

## Validation

```bash
# 1. Required protocol markers present
grep -E "append-only|SCHEMA\.md|_index\.md|contradiction" skills/ingest/SKILL.md
# Expected: 4+ matches

# 2. Trigger phrases present
grep -E "ingest this|add to wiki|process this source|update wiki with" skills/ingest/SKILL.md
# Expected: matches found

# 3. Lint clean (no failures for the new skill)
python scripts/lint.py --root .
# Expected: zero failure-severity issues for skills/ingest/SKILL.md

# 4. Full test suite unaffected
python -m pytest tests/ -v
# Expected: zero failures

# 5. Skill discoverable (name matches directory)
python -c "
import pathlib
p = pathlib.Path('skills/ingest/SKILL.md')
import sys; sys.path.insert(0, '.')
from wos.frontmatter import parse_frontmatter
fm = parse_frontmatter(p.read_text())
assert fm.get('name') == 'ingest', f'name mismatch: {fm.get(\"name\")}'
print('ok')
"
# Expected: ok
```
