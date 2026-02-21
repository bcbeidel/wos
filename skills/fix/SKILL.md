---
name: fix
description: >
  This skill should be used when the user wants to "fix issues",
  "auto-fix", "fix health problems", "regenerate manifest",
  "refresh CLAUDE.md", "clean up", "find broken files",
  "fix section order", or any request to act on health findings
  or maintain document quality.
disable-model-invocation: true
argument-hint: "[fix|regenerate|cleanup]"
---

# Fix Skill

Act on health signals by modifying project content. Audit observes;
fix acts. All write operations require user confirmation.

## Routing

Route by keyword in the user's request:

| Keyword | Workflow | What it does |
|---------|----------|-------------|
| fix / auto-fix / repair | fix-auto | Apply safe auto-corrections |
| regenerate / refresh / sync | fix-regenerate | Regenerate discovery artifacts |
| cleanup / orphan / broken | fix-cleanup | Find and remove broken files |

Default (no keyword): run **fix-auto**.

## Key Rules

- **All writes require confirmation.** Show proposed changes before applying.
- Audit is read-only -- fix is the write counterpart
- Auto-fixes re-validate via `parse_document()` after every change
- Regeneration uses the existing discovery layer (`scripts/run_discovery.py`)
