---
name: WOS Design Principles
description: 10 principles that guide WOS development, revised from the simplification (PR #38) through v0.5.0.
related:
  - artifacts/plans/2026-02-27-architecture-reference.md
---

# WOS Design Principles

## What WOS cares about

1. **Convention over configuration.** Good patterns — document structure, naming
   conventions, source hierarchies — are documented for humans and LLMs to
   follow voluntarily, not enforced in code.

2. **Structure in code, quality in skills.** The code layer checks what's
   deterministic — links resolve, frontmatter exists, indexes sync. The skill
   layer guides content quality through research rigor, source verification,
   and structured workflows. Neither does the other's job.

3. **Single source of truth.** Navigation and indexes are derived from disk
   state, never curated by hand. Anything maintained manually will drift.

## How WOS is built

4. **Keep it simple.** No class hierarchies, no frameworks, no indirection.
   When choosing between a flexible abstraction and a straightforward
   implementation, choose the straightforward one.

5. **When in doubt, leave it out.** Every required field, every abstraction,
   every feature must justify its presence. When choosing between adding
   complexity and removing a case, remove it.

6. **Omit needless words.** Every word in agent-facing output must earn its
   place. Agents consume navigation and context on every conversation —
   brevity is a feature.

7. **Depend on nothing.** The core package depends only on the standard
   library. External dependencies are isolated to scripts that declare their
   own.

8. **One obvious way to run.** Every script, every skill, same entry point.
   Consistency eliminates a class of failures.

## How WOS operates

9. **Separate reads from writes.** Audit observes and reports. Fixes require
   explicit user action. No tool modifies files as a side effect of reading
   them.

10. **Bottom line up front.** LLMs lose attention in the middle of long
    documents. Key insights go at the top and bottom. This is convention
    (principle 1), not enforcement.

## What these principles reject

- No content quality validation in the code layer
- No class hierarchies or framework patterns
- No mandatory curation (navigation is always derived)
- No runtime dependencies in the core package
- No special-case invocation patterns
