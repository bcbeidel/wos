---
name: Pipeline Quality Improvements Design
description: Four targeted improvements to the WOS research-to-context pipeline based on green-field usage analysis of two repos.
type: plan
related:
  - docs/plans/2026-02-27-architecture-reference.md
  - docs/research/2026-02-22-design-principles.md
---

# Pipeline Quality Improvements Design

**Branch:** feat/91-pipeline-quality-improvements
**Issue:** #91

## Context

Two green-field implementations of the WOS research-to-context pipeline
(context-paid-media-analyst, context-customer-experience-analyst) revealed
systemic friction points. 12 potential improvements were identified, reviewed
against the 10 design principles, and narrowed to 4 survivors plus a
follow-up issue.

## Changes

### #7: DRAFT Marker Detection in Audit

**Problem:** 6/10 research documents in paid-media-analyst retained
`<!-- DRAFT -->` markers after parallel agent execution. The audit didn't
catch this.

**Where:** `wos/validators.py`

**Design:**
- New function `check_draft_markers()` in the per-file validation path
- If `type: research` and raw content contains `<!-- DRAFT -->`, emit a warning
- Severity: `warn` — a DRAFT marker indicates incomplete workflow, not invalid
  structure. The user may have intentional work-in-progress
- Called from `validate_file()` alongside existing checks 1-4

**Tests:**
- Inline markdown with `<!-- DRAFT -->` in content, `type: research` →
  assert warning emitted
- Same content without marker → assert clean
- Non-research document with `<!-- DRAFT -->` → assert clean (only applies
  to research type)

---

### #6: Downgrade 403/429 URL Responses to Warnings

**Problem:** Paid-media audit flagged 62 URL failures, 61 were false
positives from sites blocking automated requests (403/429). Signal drowned
in noise.

**Where:** `wos/validators.py` — `check_source_urls()`

**Design:**
- `url_checker.py` unchanged — it reports what it sees (`reachable=False`
  for 403/429). Policy decisions belong in validators.
- In `check_source_urls()`, when `reachable=False`:
  - Status 403 or 429 → severity `warn`, message:
    `"URL returned {status} (site may block automated checks)"`
  - All other failures (404, 500, connection error) → severity `fail`
    (unchanged)

**Tests:**
- Mock `check_url` returning status 403 → assert `warn` severity
- Mock `check_url` returning status 429 → assert `warn` severity
- Mock `check_url` returning status 404 → assert `fail` severity
- Mock `check_url` returning status 0 (connection error) → assert `fail`

**Follow-up issue (not in scope):** Interactive cleanup flow where the agent
asks the human to verify 403/429 URLs and provide content. This belongs in
a cleanup action, not the audit itself.

---

### #5: AGENTS.md / CLAUDE.md Initialization Checks

**Problem:** CX-analyst repo created AGENTS.md without WOS markers, breaking
`agents_md.py`. Neither repo had AGENTS.md or CLAUDE.md until the user
explicitly prompted for them late in the workflow. Nothing in the audit
catches this.

**Where:** `wos/validators.py`, `skills/create/SKILL.md`, `skills/audit/SKILL.md`

**Design — Code layer** (`wos/validators.py`):

New checks in `validate_project()` (project-level, not per-file):

| Condition | Severity | Message |
|-----------|----------|---------|
| AGENTS.md missing | warn | No AGENTS.md found. Run /wos:create to initialize. |
| AGENTS.md exists, no `<!-- wos:begin -->` marker | warn | AGENTS.md lacks WOS markers. Navigation updates won't work. |
| CLAUDE.md missing | warn | No CLAUDE.md found. Run /wos:create to initialize. |
| CLAUDE.md exists, doesn't contain `@AGENTS.md` | warn | CLAUDE.md doesn't reference @AGENTS.md. Navigation may not load. |

All `warn`, not `fail` — these are structural recommendations, not hard
requirements. A project may intentionally skip AGENTS.md.

**Design — Skill layer** (`skills/create/SKILL.md`):

In section "1. Initialize Project", replace:

> Update AGENTS.md with the WOS section using markers.

With:

> Update AGENTS.md with the WOS section wrapped in `<!-- wos:begin -->` /
> `<!-- wos:end -->` markers. These markers are required — they enable
> automated navigation updates via `agents_md.py`. Never place WOS-managed
> content outside these markers.

**Design — Skill layer** (`skills/audit/SKILL.md`):

Add a "Cleanup Actions" section after "Interpreting Results":

> ## Cleanup Actions
>
> After presenting audit results, offer to help resolve actionable warnings:
>
> - **Missing AGENTS.md or CLAUDE.md:** Offer to run `/wos:create` to
>   initialize. Confirm with the user before writing any files.
> - **AGENTS.md missing WOS markers:** Offer to run `/wos:create` to add
>   the WOS-managed section. Confirm before modifying existing content.
> - **CLAUDE.md missing @AGENTS.md reference:** Offer to add the reference.
>   Do not rewrite CLAUDE.md contents — only add the `@AGENTS.md` line.

**Tests:**
- No AGENTS.md in project → assert warning
- AGENTS.md without markers → assert warning
- AGENTS.md with markers → assert clean
- No CLAUDE.md → assert warning
- CLAUDE.md without `@AGENTS.md` → assert warning
- CLAUDE.md with `@AGENTS.md` → assert clean

---

### #4: Explicit Sibling Cross-References in Distill

**Problem:** 81 context files across both repos link to their source research
document but not to each other. The `related:` template in the distill skill
uses a vague placeholder that reads as a category label, not an instruction.

**Where:** `skills/distill/SKILL.md` — step 4 (Generate)

**Design:** Replace the `related:` section of the frontmatter template:

Before:
```yaml
related:
  - [Path to source research artifact]
  - [Paths to sibling distilled files]
```

After:
```yaml
related:
  - [Path to source research artifact]
  - [Path to other context file from this batch]
  - [Path to existing context file in the same area]
```

Add after the template:

> Every distilled file should link to at least one sibling context file in
> `related:`, not just the source research document. When distilling a batch,
> include cross-references between thematically adjacent files.

Convention (P1), not enforcement. The audit does not check for this.

**Tests:** None — skill text change only.

---

## Principles Alignment

| Change | Principles |
|--------|-----------|
| #7 DRAFT detection | P2 (structural check in code), P9 (audit observes) |
| #6 URL severity | P2 (structural check in code), P4 (keep it simple) |
| #5 AGENTS/CLAUDE checks | P2 (structural check), P9 (audit observes, create writes), P1 (convention) |
| #4 Distill related | P1 (convention over configuration) |

## Rejected During Review

| Proposal | Why rejected | Principle |
|----------|-------------|-----------|
| Runtime directory detection (`artifacts/` vs `docs/`) | Issue #84 already resolved; detection logic adds indirection | P4, P8 |
| Batch mode in research/distill skills | Wrong location — parallel agents don't read the skill | P6 |
| Post-distillation review step | Already exists (distill step 5 runs audit) | P5 |
| Cross-reference density check in audit | Content quality validation in code layer | P1, P2 |
| Commit cadence guidance | Out of WOS scope — developer workflow | P5 |
| Pipeline reference document | Premature abstraction — pattern emerges naturally | P4, P5 |

## Files Touched

- `wos/validators.py` — 3 new checks (#7, #6, #5)
- `skills/audit/SKILL.md` — cleanup actions section (#5)
- `skills/create/SKILL.md` — marker requirement clarification (#5)
- `skills/distill/SKILL.md` — related template + guidance (#4)
- `tests/test_validators.py` — tests for #7, #6, #5
