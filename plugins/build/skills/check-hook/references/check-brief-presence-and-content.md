---
name: Brief Presence and Content
description: A `.briefs/<hook-name>.brief.md` exists, carries the five required H2 sections, and the *So-what* names a specific enforcement gap rather than a category description.
paths:
  - "**/.briefs/*.brief.md"
---

Every hook has a `.briefs/<hook-name>.brief.md` at the repo root with five H2 sections — *User ask*, *So-what*, *Scope boundaries*, *Planned artifacts*, *Planned handoffs* — and the *So-what* names a specific scenario the hook prevents (a real near-miss or a class of mistakes the team kept making).

**Why:** Briefs are throw-away build records, but a missing or generic brief leaves the build untraceable to its original intent. Six months later, when a hook fires unexpectedly, the team needs to know whether the enforcement was a deliberate response to a 2026-04-22 incident or a category-level "we should probably block X" instinct that no one will defend. A *So-what* like "deterministically enforces X" reads as the latter and gives the next maintainer no anchor for keep/drop decisions. Severity: `warn` (presence and content). Hooks built before the brief pattern existed will trip this; a retroactive brief is acceptable.

**How to apply:** for missing-or-incomplete-presence, write or extend `.briefs/<hook-name>.brief.md` per the toolkit's brief template — five H2 sections, scoped concretely. For generic *So-what*, ask the user for the specific scenario — a real near-miss, a class of mistakes the team kept making — and rewrite the paragraph anchored in those specifics. *Scope boundaries* lists concrete in/out items, not abstract categories.

```markdown
# block-direct-main-push hook brief

## User ask
Block `git push` to `main` from agent sessions; allow CI.

## So-what
On 2026-04-22 the agent pushed an in-progress refactor directly to `main`,
breaking deploy for ~40 minutes. The team's existing CLAUDE.md advisory
("don't push to main") was insufficient under time pressure — the hook
turns the advisory into a deterministic block.

## Scope boundaries
In: `git push origin main`, `git push origin HEAD:main`.
Out: `gh pr merge` (intentional), CI invocations (NO_BLOCK env var).
...
```

**Common fail signals (audit guidance):**
- `.briefs/<hook-name>.brief.md` does not exist.
- One or more of the five H2 sections is absent (*User ask*, *So-what*, *Scope boundaries*, *Planned artifacts*, *Planned handoffs*).
- *So-what* reads as a category description ("deterministically enforces X", "prevents bad commits") rather than a specific scenario.
- *Scope boundaries* is empty, vague ("standard cases"), or missing the in/out distinction.
- Brief filename does not match the hook script's basename.

**Exception:** hooks scaffolded before the brief pattern existed are exempt from presence checking, but a retroactive brief is encouraged when the hook is next modified.
