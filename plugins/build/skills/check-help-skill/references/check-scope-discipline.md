---
name: Scope Discipline
description: The help-skill stays inside its scope (synopsis, index, workflows, pointers) and does not spill into AGENTS.md or README territory.
paths:
  - "**/skills/help/SKILL.md"
---

Keep the help-skill body to synopsis, skill index, workflows, and pointers — push architectural prose to AGENTS.md and install/contributing prose to the README.

**Why:** Pointers, not duplications. A help-skill that grows a "Why this plugin exists" section duplicates AGENTS.md territory; one that grows an "Installation" section duplicates README territory. Both copies then drift — the help-skill's version goes stale because the canonical doc is updated and the help-skill is forgotten, or vice versa. The caller ends up with two contradictory sources and no way to know which is current. The help-skill's distinct value is the curated index + triage scaffolding; everything else has a better home, and the body length budget (~150 lines) is the forcing function.

**How to apply:** When a section title resembles "Why this plugin exists", "Architecture", "Design philosophy", "Plugin composition", "Installation", "Setup", "Contributing", "License", or "Changelog", the content belongs elsewhere — replace it with a pointer in `## Where to look next`. The four allowed body sections are: synopsis (one sentence below H1), skill index (managed-region table), `## Common workflows` (curated chains), and `## Where to look next` (pointers). Anything else WARNs. Severity: `warn`.

```markdown
## Where to look next

- [AGENTS.md](../../../../AGENTS.md) — plugin composition rationale
- [README.md](../../../../README.md) — install + contributing
- [CONTRIBUTING.md](../../../../CONTRIBUTING.md) — contribution flow
```

**Common fail signals (audit guidance):**
- `## Why this plugin exists` / `## Architecture` / `## Design` — AGENTS.md spillage.
- `## Installation` / `## Setup` / `## Prerequisites` — README spillage.
- `## Contributing` / `## License` / `## Changelog` — repo-meta spillage.
- Body line count climbs above 150 with sections that are not synopsis/index/workflows/pointers.
- Architectural rationale paragraphs embedded inside `## Common workflows` qualifiers.
