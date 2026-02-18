---
document_type: plan
description: "Sequenced build roadmap for work-os with session protocol, dependency tracking, and phase-level entry/exit criteria"
last_updated: 2026-02-17
status: active
related:
  - artifacts/plans/v0.1-foundation/1.1-document-type-models.md
  - artifacts/plans/v0.1-foundation/1.2-discovery-layer.md
  - artifacts/plans/v0.1-foundation/2.1-skill-setup.md
  - artifacts/plans/v0.1-foundation/3.1-skill-curate.md
  - artifacts/plans/v0.1-foundation/2.2-skill-health.md
  - artifacts/plans/v0.1-foundation/3.2-skill-maintain.md
  - artifacts/plans/v0.1-foundation/4.1-skill-report-issue.md
  - artifacts/plans/v0.1-foundation/5.1-skill-research.md
  - artifacts/plans/v0.1-foundation/4.2-skill-consider.md
  - artifacts/plans/v0.1-foundation/6.1-skill-observe.md
---

# Work-OS Build Roadmap

## Session Protocol

At the start of every session:

1. **Read this file.** Check the status table below for the first phase not
   marked `done`.
2. **Read that phase's plan.** The plan file has Steps and Verification
   sections — those are your implementation spec.
3. **Verify entry criteria.** If the phase has prerequisites, confirm they
   pass before starting (run the prior phase's verification commands).
4. **Research before building.** For skill phases (2.1+), search for
   existing implementations to learn from before writing code. Look for
   well-starred repos, established Claude Code plugins, and similar tools.
   Bias toward battle-tested patterns over inventing from scratch. Document
   findings and how they inform the implementation.
5. **Implement the plan.** Follow the steps. Run tests as you go.
6. **Run exit criteria.** Every verification item in the plan must pass.
7. **Update this file.** Change the phase status to `done` and commit.
8. **If time remains,** move to the next phase.

If a phase is too large for one session, update its status to `in-progress`
and note what's complete in the Comments column. The next session picks up
where you left off.

## Status

| Phase | Plan | Status | Comments |
|-------|------|--------|----------|
| 1.1 | [Document Type Models](1.1-document-type-models.md) | done | 48 tests, ruff clean |
| 1.2 | [Discovery Layer](1.2-discovery-layer.md) | done | 30 tests, ruff clean |
| 2.1 | [Setup Skill](2.1-skill-setup.md) | done | 22 tests, ruff clean, plugin renamed to wos |
| 2.2 | [Health Skill](2.2-skill-health.md) | done | 54 tests, ruff clean, CLI produces valid JSON |
| 3.1 | [Curate Skill](3.1-skill-curate.md) | done | 18 tests, ruff clean, round-trip validation |
| 3.2 | [Maintain Skill](3.2-skill-maintain.md) | not started | |
| 4.1 | [Report-Issue Skill](4.1-skill-report-issue.md) | not started | |
| 4.2 | [Consider Skill](4.2-skill-consider.md) | not started | |
| 5.1 | [Research Skill](5.1-skill-research.md) | not started | |
| 6.1 | [Observe Skill](6.1-skill-observe.md) | not started | |

## Dependency Graph

```
Phase 1 - Foundation (sequential)
  1.1  Document Type Models          <- no dependencies
  1.2  Discovery Layer               <- requires 1.1

Phase 2 - Core Infrastructure (parallel after phase 1)
  2.1  Setup Skill                   <- requires 1.1 + 1.2
  2.2  Health Skill                  <- requires 1.1 only

Phase 3 - Content & Maintenance (parallel after phase 2)
  3.1  Curate Skill                  <- requires 1.1 + 1.2 + 2.1
  3.2  Maintain Skill                <- requires 1.2 + 2.2

Phase 4 - Standalone Skills (no ordering constraint)
  4.1  Report-Issue Skill            <- independent
  4.2  Consider Skill                <- independent

Phase 5 - Capability
  5.1  Research Skill                <- requires 1.1 + 3.1

Phase 6 - Extended
  6.1  Observe Skill                 <- requires 2.2 + 3.2
```

Phases 4.1 and 4.2 are independent — they can be built at any point without
waiting for other phases. Insert them whenever you want a change of pace or
need to parallelize work.

## Phase Details

### Phase 1.1 — Document Type Models

**Plan:** [1.1-document-type-models.md](1.1-document-type-models.md)

**Entry criteria:** None. This is the foundation.

**What you're building:** Project tooling (`pyproject.toml`, ruff config, GitHub
Actions CI) and `wos/document_types.py` — Pydantic v2 models for all four
document types (topic, overview, research, plan), a discriminated union
`parse_document()` function, and structural dispatch tables (SECTIONS,
SIZE_BOUNDS, DIRECTORY_PATTERNS).

**Exit criteria:**
- `pyproject.toml` exists with pydantic + ruff + pytest deps
- `python3 -c "from wos.document_types import parse_document, DocumentType"` succeeds
- `python3 -m pytest tests/test_document_types.py -v` passes
- `ruff check wos/ tests/` passes
- Missing required fields raise `ValidationError` with clear messages
- Research documents parse without `last_validated`
- GitHub Actions CI runs pytest + ruff on push

**Why first:** Every other component imports from this module. Nothing works
without it.

---

### Phase 1.2 — Discovery Layer

**Plan:** [1.2-discovery-layer.md](1.2-discovery-layer.md)

**Entry criteria:** Phase 1.1 `done`. `parse_document()` importable.

**What you're building:** `wos/discovery.py` — generates the CLAUDE.md
manifest (marker-delimited under `## Context`), the
`.claude/rules/work-os-context.md` rules file, and mirrors to AGENTS.md. All
derived from files on disk.

**Exit criteria:**
- `python3 scripts/run_discovery.py` produces correct manifest
- Existing content outside markers preserved
- Rules file exists and is under 50 lines
- Running twice produces identical output (idempotent)
- AGENTS.md matches CLAUDE.md manifest

---

### Phase 2.1 — Setup Skill

**Plan:** [2.1-skill-setup.md](2.1-skill-setup.md)

**Entry criteria:** Phases 1.1 and 1.2 `done`.

**What you're building:** `skills/setup/` — SKILL.md, workflows for init and
add-area, `wos/scaffold.py` for directory creation.

**Exit criteria:**
- `/wos:setup` on fresh directory creates full structure
- CLAUDE.md exists with `## Context` manifest and markers
- Each area has valid `_overview.md`
- Adding areas doesn't disturb existing content
- `python3 -m pytest tests/test_scaffold.py -v` passes

---

### Phase 2.2 — Health Skill

**Plan:** [2.2-skill-health.md](2.2-skill-health.md)

**Entry criteria:** Phase 1.1 `done`. (Does not need discovery layer.)

**What you're building:** `skills/health/` — type-dispatched validators,
cross-validators, Tier 2 triggers, CLI entry point. The dispatch tables in
`document_types.py` control which validators run for which document type.

**Exit criteria:**
- `python3 scripts/check_health.py` outputs valid JSON
- Missing `sources` in topic → `severity: fail`
- Missing `## Verification` in plan → `severity: warn`
- Research documents NOT checked by `check_last_validated`
- Broken `related` links → `severity: fail`
- CI exit code 1 on `severity: fail`
- All validator tests pass

---

### Phase 3.1 — Curate Skill

**Plan:** [3.1-skill-curate.md](3.1-skill-curate.md)

**Entry criteria:** Phases 1.1, 1.2, and 2.1 `done`.

**What you're building:** `skills/curate/` — free-text intake, intent
classification, document creation/update for all 4 types, template rendering,
manifest regeneration after context-type changes.

**Exit criteria:**
- Intent routing: "investigate X" → research, "plan Y" → plan
- Created documents pass `parse_document()` validation
- CLAUDE.md updates after topic/overview creation (not after research/plan)
- Templates produce valid output for all 4 types
- `python3 -m pytest tests/test_templates.py -v` passes

---

### Phase 3.2 — Maintain Skill

**Plan:** [3.2-skill-maintain.md](3.2-skill-maintain.md)

**Entry criteria:** Phases 1.2 and 2.2 `done`.

**What you're building:** `skills/maintain/` — auto-fix, lifecycle transitions,
manifest regeneration, cleanup. All write operations require user confirmation.

**Exit criteria:**
- `maintain-fix` corrects section order and passes `parse_document()`
- `maintain-lifecycle` updates plan status and `last_updated`
- `maintain-regenerate` updates CLAUDE.md to match disk state
- `maintain-cleanup` identifies unparseable files
- `python3 -m pytest tests/test_auto_fix.py -v` passes

---

### Phase 4.1 — Report-Issue Skill

**Plan:** [4.1-skill-report-issue.md](4.1-skill-report-issue.md)

**Entry criteria:** None. Independent of all other phases.

**What you're building:** `skills/report-issue/` — gather context, classify
issue type, draft GitHub issue, preview, submit via `gh`.

**Exit criteria:**
- "I found a bug" triggers the submit workflow
- Draft includes relevant context
- User sees preview before submission
- `gh issue create` only called after explicit approval
- Missing `gh` produces setup instructions, not a crash

---

### Phase 4.2 — Consider Skill

**Plan:** [4.2-skill-consider.md](4.2-skill-consider.md)

**Entry criteria:** None. Independent of all other phases.

**What you're building:** `skills/consider/` — 16 mental model files. Each is
an independent `.md` file (~45 lines) with uniform structure.

**Exit criteria:**
- `skills/consider/models/` contains 16 `.md` files
- Each has YAML frontmatter with `description` and `argument-hint`
- Each has 4 sections: objective, process, output_format, success_criteria
- Each file under 60 lines
- All 16 follow identical structure

---

### Phase 5.1 — Research Skill

**Plan:** [5.1-skill-research.md](5.1-skill-research.md)

**Entry criteria:** Phases 1.1 and 3.1 `done`.

**What you're building:** `skills/research/` — SIFT-based investigation with
8 modes (deep dive, landscape, technical, feasibility, competitive, options,
historical, open source). Produces research documents via curate.

**Exit criteria:**
- "What do we know about X?" → deep dive mode detected
- Research output passes `parse_document()` validation
- Sources include authority annotations
- Counter-evidence section present when mode requires it
- Source hierarchy referenced during evaluation

---

### Phase 6.1 — Observe Skill

**Plan:** [6.1-skill-observe.md](6.1-skill-observe.md)

**Entry criteria:** Phases 2.2 and 3.2 `done`.

**What you're building:** `skills/observe/` — PostToolUse hook for auto-capture,
utilization data layer, recommendations engine (6 categories), dashboard and
trends workflows.

**Exit criteria:**
- Hook fires on Read and appends to `.work-os/utilization/log.jsonl`
- Hook never crashes (exits 0 on errors)
- `read_utilization()` returns correct counts
- `generate_recommendations()` with insufficient data returns `skipped`
- Stale-high-use fires at 50+ reads with `last_validated` > 90 days
- Never-referenced fires at 0 reads after 14+ days
- `python3 -m pytest tests/test_utilization.py tests/test_recommendations.py -v` passes

## Starting Prompt

Copy this into your first session in the work-os repo:

> Read `artifacts/plans/v0.1-foundation/_roadmap.md` and follow the session protocol. Find the
> first phase not marked `done`, read its plan, implement it, run verification,
> and update the roadmap status.
