# Report-Issue Skill Improvements Design

**Date:** 2026-02-18
**Issue:** #14
**Branch:** `issue/14-improve-report-issue`

## Problem

The `/wos:report-issue` skill produces structurally complete but low-quality
issues. Three gaps: the agent cannot invoke it proactively, templates lack
evaluation criteria and scope boundaries, and drafts use consumer-specific
framing instead of tool-author framing.

Issues #5, #8, #9 all required significant rewrites. Issue #12 was written
with quality standards from the start and required none.

## Design Decisions

- **Quality checklist is advisory, not blocking.** Checks are shown in the
  preview alongside the draft. The user can approve and submit even with
  warnings. This keeps the user in control.
- **Feedback stays lightweight.** Only the generic-framing check applies to
  feedback issues. Feedback is a low-friction entry point; if substantive,
  the agent suggests reclassifying as a feature request during Phase 3.
- **Checklist lives in Phase 5 (Preview), not Phase 4 (Draft).** The agent
  applies checks after drafting and shows results in the preview block. No
  separate review phase needed.
- **Framing guidance lives in Phase 4 (Draft).** The agent applies framing
  rules while writing, not after.

## Changes

### 1. SKILL.md — Enable LLM Invocation

Remove `disable-model-invocation: true`. Update description to cover
proactive detection:

```yaml
description: >
  Use when the user wants to "report a bug", "submit feedback",
  "request a feature", "file an issue", or when you discover
  a problem, limitation, or missing capability in WOS during
  normal work. Proactively suggest filing when you encounter
  WOS issues the maintainer should know about.
```

### 2. issue-templates.md — Updated Templates

**Bug Report** — replace "Steps to Reproduce" with MRE section:

- Description
- Minimum Reproducible Example (minimal fixture + exact command + exact
  error output; if multiple files needed, describe minimal directory
  structure)
- Expected Behavior
- Actual Behavior
- Environment (auto-gathered)

**Feature Request** — replace 4-section template with 7 sections:

- Problem (generic framing, any WOS user should recognize it)
- Why This Matters (impact bullets from tool's perspective)
- Proposed Solution (with before/after examples where behavior changes,
  design decisions for non-obvious choices)
- Scope / Non-Goals (what's included, what's explicitly excluded)
- Evaluation (test fixtures table + pass criteria table)
- Alternatives Considered
- Environment (auto-gathered)

**General Feedback** — unchanged (Context/Observation/Suggestion/Environment).

### 3. report-issue-submit.md — Framing Guidance (Phase 4)

Add framing rule to Phase 4 drafting instructions:

- Write from WOS tool author's perspective, not consumer's
- Replace vault-specific details with generic examples
- Use "a WOS user" / "a project with N context files" instead of "I" / "my vault"
- Describe solutions in terms of WOS internals (scripts, validators, skills)
- Extract generic patterns from consumer-specific context

### 4. report-issue-submit.md — Quality Checklist (Phase 5)

Add quality checklist to preview. Agent applies checks and shows results:

| Check | Applies to | What it catches |
|---|---|---|
| Generic framing | All types | Vault-specific paths, file counts, "my vault" language |
| Self-contained | All types | Understandable without external context |
| Has evaluation criteria | Feature requests | Test fixtures and pass criteria present |
| Has MRE | Bug reports | Minimal reproducible example present |
| Has before/after examples | Features changing behavior | Current vs proposed shown |
| Has scope/non-goals | Feature requests | Boundaries defined |

Preview format:

```
──────────────────────────────────────
Title: [title]
Labels: [labels]
Repo: bcbeidel/wos
──────────────────────────────────────
[full issue body]
──────────────────────────────────────

Quality Checks:
  ✓ Generic framing
  ✓ Self-contained
  ⚠ Missing evaluation criteria
  ✓ Scope/Non-Goals present
```

All checks are advisory — user can override.

## Files Changed

| File | Change |
|---|---|
| `skills/report-issue/SKILL.md` | Remove `disable-model-invocation`, update description |
| `skills/report-issue/references/issue-templates.md` | New bug/feature templates |
| `skills/report-issue/references/report-issue-submit.md` | Framing guidance in Phase 4, quality checklist in Phase 5 |

## Scope

- Three files modified, no new files
- No changes to Phases 1-3 or Phase 6
- No scripted validation (all agent-applied)
- No new issue types

## Non-Goals

- No automated linting of issue content
- No changes to target repo or submission mechanism
- No changes to general feedback template structure
