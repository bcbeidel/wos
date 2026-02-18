---
name: maintain
description: >
  This skill should be used when the user wants to "fix issues",
  "auto-fix", "fix health problems", "update status", "change status",
  "transition to active", "regenerate manifest", "refresh CLAUDE.md",
  "clean up", "find broken files", "fix section order", or any request
  to act on health findings or maintain document quality.
disable-model-invocation: true
argument-hint: "[fix|lifecycle|regenerate|cleanup]"
---

# Maintain Skill

Act on health signals by modifying project content. Health observes;
maintain acts. All write operations require user confirmation.

## Routing

Route by keyword in the user's request:

| Keyword | Workflow | What it does |
|---------|----------|-------------|
| fix / auto-fix / repair | maintain-fix | Apply safe auto-corrections |
| lifecycle / status / transition | maintain-lifecycle | Update plan status |
| regenerate / refresh / sync | maintain-regenerate | Regenerate discovery artifacts |
| cleanup / orphan / broken | maintain-cleanup | Find and remove broken files |

Default (no keyword): run **maintain-fix**.

## Key Rules

- **All writes require confirmation.** Show proposed changes before applying.
- Health is read-only — maintain is the write counterpart
- Auto-fixes re-validate via `parse_document()` after every change
- Lifecycle transitions enforce valid paths (e.g., draft -> active -> complete)
- Regeneration uses the existing discovery layer (`scripts/run_discovery.py`)
