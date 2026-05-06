---
name: Scope Discipline
description: A subagent does one well-defined thing and names both what it handles and what it refuses.
paths:
  - "**/.claude/agents/**/*.md"
  - "**/agents/**/*.md"
---

A subagent does one well-defined thing and names both what it handles and what it refuses.

**Why:** Single-responsibility subagents route deterministically. Mixed-scope agents — "lint TypeScript and also generate migrations" — produce ambiguous routing, bloated prompts, and unclear failure modes. Out-of-scope is as load-bearing as in-scope: it tells the agent when to stop rather than improvise. Source principles: *Single responsibility.* *Scope and out-of-scope stated explicitly.*

**How to apply:** Confirm the description and body cover one workflow over one artifact type. Add an explicit Scope / Out-of-scope section (or equivalent) naming both what the agent handles and what it refuses or escalates. If the description joins distinct capabilities with "and", split into two subagents.

```markdown
## Scope

In scope: TypeScript files (`.ts`, `.tsx`) currently staged.
Out of scope: untracked files, test files, generated code.
```

**Common fail signals (audit guidance):**
- Description or body contains an "and/or" joining distinct workflows.
- No Scope / Out-of-scope section (or equivalent) in the body.
- Workflow covers multiple distinct artifacts (produces both a report and a migration, for example).
