---
name: Trigger Conditions
description: `## When to use` must list concrete, scannable conditions a reader can match against — not a restatement of the description.
paths:
  - "**/SKILL.md"
---

Declare triggers as scannable conditions — each bullet names a specific user phrase, file pattern, error string, or lifecycle event the reader can confirm without inference.

**Why:** The `description` retrieves; `## When to use` confirms. Bullets that restate the description in different words waste the section's budget and add no routing signal — the reader still cannot decide whether the skill applies. Abstract bullets ("when the user needs data transformation") force re-derivation at every reference; concrete bullets ("the user pastes a `.csv` path and asks for Parquet output") let the agent match observed conditions to a list and stop.

**How to apply:** Rewrite each bullet to name a concrete trigger not already in the description. Aim for multiple scannable bullets — each pointing at a specific user phrase, file pattern, error string, or lifecycle event. If a single bullet covers everything, the trigger surface is too narrow or the bullet is too abstract.

```markdown
## When to use
- The user pastes a `.csv` path and asks for Parquet output
- A data pipeline step requires columnar storage for downstream queries
- A notebook loads a CSV and hits memory pressure — Parquet reduces it
```

**Common fail signals (audit guidance):**
- Bullets restate the description in different words without adding specificity
- Bullets are abstract ("when the user needs data transformation") with no concrete trigger phrase, file type, or condition
- Section contains only one bullet and it's generic
