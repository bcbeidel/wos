---
name: Workflow Curation
description: The `## Common workflows` section carries composed chains, not a flat re-listing of skills, and each chain names the user task it applies to.
paths:
  - "**/skills/help/SKILL.md"
---

The `## Common workflows` section must contain at least one composed chain (skill-a → skill-b → skill-c) with a one-sentence "when this chain applies" qualifier — never a flat enumeration of skills.

**Why:** A help-skill without curated chains is just a re-listing of the skill table — the index above it already covers that. The chain is what differentiates triage scaffolding from a directory listing: it tells the caller how skills compose, which is what the table cannot show. A workflows section that re-lists the skill names trains callers to ignore the section entirely, and the help-skill collapses into a flat directory of siblings — losing its load-bearing job of routing the caller to the right entry point.

**How to apply:** Each entry in `## Common workflows` must (a) name a user task ("Build new feature", "Audit a script"), (b) show ≥2 skills connected with `→` arrows, and (c) include a one-sentence qualifier saying when the chain applies. A bullet that names a single skill, or that re-lists every skill in the plugin without composition, fails this dimension. Two or three chains is the right number — more dilutes signal, none defeats the section's purpose. Severity: `warn`.

```markdown
## Common workflows

- **Build new feature** — `scope-work` → `plan-work` → `start-work` → `verify-work`.
  *Use when starting from requirements.*
- **Fix a bug** — `start-work` → `verify-work`. *Use when the issue is already triaged.*
```

**Common fail signals (audit guidance):**
- Section bullets are single skill names with no `→` connector — flat listing, not chain.
- Section is a re-paste of the skill-index table with reordered rows.
- Chains are listed but no per-chain "when this applies" qualifier.
- Generic chain names like "Workflow A", "Standard process" — abstract enumeration, not user tasks.
- Workflows section omitted entirely while the skill index is present.
