---
document_type: plan
description: "Build the report-issue skill for submitting feedback, bug reports, and feature ideas back to the Dewey source repo via GitHub"
last_updated: 2026-02-17
status: draft
related:
  - ../research/2026-02-17-skills-architecture-design.md
---

# Build Report-Issue Skill

## Objective

A `/dewey:report-issue` skill exists that lets users submit feedback, bug
reports, and feature ideas back to the Dewey source repository. It gathers
context from the user's knowledge base usage, classifies the issue type,
drafts a GitHub issue with relevant details, and submits via `gh` CLI after
user preview and approval.

## Context

- Skills architecture: `artifacts/research/2026-02-17-skills-architecture-design.md` §3.2
- Independent of other skills — no dependencies on document type models
- Requires `gh` CLI installed and authenticated
- Linear workflow, no conditional routing

## Steps

1. Create `skills/report-issue/SKILL.md` with skill description,
   conversational triggers ("report a bug", "submit feedback", "request a
   feature", "file an issue"), linear routing to single workflow

2. Create `skills/report-issue/workflows/report-issue-submit.md`:
   - Phase 1: Gather — ask what happened, what was expected, what context
     is relevant. Collect error messages, file paths, reproduction steps
   - Phase 2: Classify — determine issue type (bug, feature, feedback) and
     suggest appropriate labels
   - Phase 3: Draft — compose GitHub issue with title, description, steps
     to reproduce (for bugs), use case (for features), relevant context
     (Dewey version, knowledge base structure, document types involved)
   - Phase 4: Preview — show formatted issue to user for review and edits
   - Phase 5: Submit — run `gh issue create` with title, body, and labels
     against the Dewey repo. Show issue URL on success

3. Create `skills/report-issue/references/issue-templates.md`:
   - Bug report template (steps to reproduce, expected vs. actual, environment)
   - Feature request template (use case, proposed solution, alternatives)
   - General feedback template (context, observation, suggestion)

4. Verify `gh` availability: workflow checks for `gh auth status` before
   proceeding, suggests setup if not authenticated

## Verification

- `/dewey:report-issue` with "I found a bug" triggers the submit workflow
- Draft issue includes Dewey version and relevant context
- User sees formatted preview before submission
- `gh issue create` is only called after explicit user approval
- Missing `gh` CLI produces helpful setup instructions, not a crash
