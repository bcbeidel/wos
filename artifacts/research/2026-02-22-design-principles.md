---
name: WOS Design Principles
description: 10 principles that guide WOS development, distilled from the simplification (PR #38) and ongoing design decisions.
---

# WOS Design Principles

## What WOS cares about

1. **Opinionated about organization, hands-off about content.** WOS enforces discoverability — frontmatter, indexes, directory structure — but never inspects or validates what is inside a document.

2. **Minimal required metadata.** Only `name` and `description` are required. Every mandatory field is borne by every document forever, so each one must justify itself.

3. **Auto-generated navigation.** `_index.md` files and the AGENTS.md managed section are generated from disk state, not curated by hand. Navigation maintained manually will drift.

4. **Convention over enforcement.** Good patterns (lost-in-the-middle structure, source hierarchies, date-prefixed filenames) are documented for humans and LLMs to follow voluntarily.

## How WOS is built

5. **Flat and simple code.** One `Document` dataclass, no subclasses, no inheritance. Five source files, five validation checks.

6. **Token-conscious.** The AGENTS.md section is ~160 tokens. Every word in agent-facing output must earn its place — agents consume this on every conversation.

7. **Prefer deletion to addition.** The simplification from 23 classes to 1 dataclass is the founding act of this project's current form. When choosing between adding complexity and removing a case, remove it.

## How WOS operates

8. **Read-only audit, opt-in fix.** Audit observes and reports. Fixes require explicit user action. No tool modifies files as a side effect of reading them.

9. **Verify sources programmatically.** Research documents require cited URLs, checked via HTTP at creation and during audit. Source quality is the one content concern WOS enforces because broken links degrade all downstream consumers silently.

10. **Write for the lost middle.** LLMs lose attention in the middle of long documents. WOS documents put key insights at top and bottom. This is convention (principle 4), not enforcement, but central enough to be a principle.

## What these principles reject

- No content quality validation (no section ordering, prose checking, or staleness thresholds)
- No type-specific behavior beyond research sources
- No class hierarchies or framework patterns
- No mandatory curation (navigation is always auto-generated)
