---
name: update-context
description: >
  This skill should be used when the user wants to "restructure areas",
  "rename an area", "merge areas", "split an area", "move topics between
  areas", or "reorganize context structure".
disable-model-invocation: true
argument-hint: "[restructure operation]"
---

# Update Context Skill

Restructure existing context areas -- rename, merge, split, or move topics
between areas.

## Routing

Route by keyword in the user's request:

| Keyword | Operation | What it does |
|---------|-----------|-------------|
| rename | rename-area | Rename an area directory and update references |
| merge | merge-areas | Combine two areas into one |
| split | split-area | Divide an area into two or more |
| move | move-topics | Move topics between areas |

## Key Rules

- **All restructuring requires confirmation.** Show proposed changes before applying.
- After any restructuring, run discovery to update manifests:
  ```bash
  python3 scripts/run_discovery.py --root .
  ```
- Preserve document content and frontmatter during moves
- Update `related` links if paths change
- Update overview topic lists after moves
