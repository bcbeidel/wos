---
name: Brief Presence and Content
description: A `.briefs/<slug>.brief.md` should exist with the five required H2 sections and a specific (non-generic) So-what.
paths:
  - "**/.briefs/*.brief.md"
---

**Why:** Briefs make builds traceable to original intent. A missing brief leaves the resolver untraceable: future maintainers see a routing table without knowing which recurring problem it solved, so the rationale for individual rows is lost the first time someone questions them. A generic *So-what* ("documents the resolver for this repo") defeats the same purpose — the build becomes untraceable to the actual problem. Vague *Scope boundaries* invite scope creep. Briefs are throw-away, but during the build they are load-bearing.

**How to apply:** Locate `.briefs/<slug>.brief.md`. If absent, write a retroactive brief naming the specific filing/context drift the resolver was built to address — *Planned artifacts* and *Planned handoffs* checklists can be marked complete after the fact since briefs are throw-away. Verify all five H2 sections are present. Read *So-what*: it must name a specific gap (e.g., "team kept filing research into `.context/` because the convention was undocumented") rather than describing the category of work. Read *Scope boundaries*: *In* and *Out* lists must carry concrete items (filing rows, context bundles, named recurring tasks), not "the usual".

```markdown
## User ask
Set up dynamic context routing for the toolkit repo.

## So-what
Team members kept filing research investigations into `.context/` because
the convention was undocumented; this resolver makes filing rules
first-class so future investigations land in `.research/` automatically.

## Scope boundaries
**In:** filing rules for `.research/`, `.plans/`, `.designs/`; context bundles for hook authoring, skill authoring.
**Out:** nested resolvers in subdirectories; eval automation in CI.

## Planned artifacts
- [x] RESOLVER.md
- [x] .resolver/evals.yml

## Planned handoffs
- [x] AGENTS.md pointer added
```

**Common fail signals (audit guidance):**
- Brief is missing entirely (resolver was scaffolded before the brief pattern, or Step 0 was skipped).
- One or more of the five required H2 sections is absent.
- *So-what* reads as a category description ("documents the resolver for this repo") rather than a specific intent (the recurring task that motivated dynamic context routing here).
- *Scope boundaries* is empty or carries vague hedges.

**Exception:** N/A is acceptable when the brief is intentionally absent — for example, a resolver pre-dating the brief pattern with no impending re-build. A missing brief does not break the resolver; it leaves the build untraceable.
