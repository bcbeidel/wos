---
name: Single Concern
description: One rule, one topic — every section advances the same convention; every `paths:` glob targets files where every directive applies.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

Cover one topic per file. Every `##` section advances the same convention; every `paths:` glob targets files where every directive in the body applies.

**Why:** A file that mixes unrelated conventions is two rules masquerading as one. Mixing topics makes path-scoping impossible (each topic might apply to different files), grows the file beyond the size guidance, and breaks the discovery handle — future maintainers grep for `commit-messages.md` when looking for commit conventions, not inside `api-design.md`. A `paths:` union of unrelated patterns also wastes effort: Claude loads the API section when reading test files (and vice versa).

**How to apply:** When multiple top-level `##` sections cover topics that wouldn't naturally co-evolve (e.g., "API design" + "Test naming" + "Deployment"), split into separate files. When the filename describes one topic but the body covers another in addition, move the off-topic content to a file matching its actual topic — or to `.claude/CLAUDE.md` if it's a project-wide standard. When `paths:` is a union of unrelated patterns where each `##` section applies to only one, split the rule so each file's `paths:` covers only the directives in that file.

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API Handler Conventions

<all sections about API handlers, no test or deployment content>
```

**Common fail signals (audit guidance):**
- Multiple top-level `##` sections covering distinct topics that wouldn't naturally co-evolve (e.g., "API conventions" and "Test conventions" in the same file)
- Filename describes one topic but body covers another in addition
- Two unrelated `paths:` patterns where each `##` section applies to only one (split signal)
