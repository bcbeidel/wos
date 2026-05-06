---
name: Dual Audience
description: The help-skill reads cleanly for both a human typing `/<plugin>:help` and an agent that matched the trigger and needs triage scaffolding.
paths:
  - "**/skills/help/SKILL.md"
---

Write the help-skill so it scans cleanly for both audiences — short, scannable, with enough context to route without forcing the reader into adjacent files.

**Why:** Two audiences read this file: a human typing `/<plugin>:help` who wants a readable index, and an agent that has matched the trigger and needs triage scaffolding. A help-skill written purely for an LLM (terse, abbreviated, optimized for token cost) fails the human-readability check — the human pastes back "what does any of this mean?" A help-skill written purely for human reading (long-form, narrative, marketing-flavored) fails the agent-routing check — the agent loads more context than it needs and still has to triangulate. Both audiences must scan it cleanly; optimizing for one breaks the other.

**How to apply:** Use scannable structure (bullets, tables, short headings) for human readers and concrete trigger phrases / explicit task→skill mappings for agent routing. Trim narrative prose; keep imperatives. The pass criterion is *both* — short, structured, with the right amount of context that neither audience has to load adjacent files. Read the body twice: once as a human looking for "what does this plugin do and where do I start?", once as an agent looking for "given this user request, which skill do I dispatch?" If either pass requires loading another file, this dimension WARNs. Severity: `warn`.

```markdown
# /build:help

Author and audit Claude Code primitives — skills, hooks, rules, subagents, scripts.

## Skills in this plugin
<!-- generated table: triggers visible at a glance -->

## Common workflows
- **Build new feature** — `scope-work` → `plan-work` → `start-work`. *Use when…*
```

**Common fail signals (audit guidance):**
- Multi-paragraph narrative under headings — human-only, agent struggles to parse.
- Telegraphed bullet lists with no explanatory verbs — agent-only, human can't orient.
- Marketing prose ("This plugin empowers teams to…") — fails both audiences.
- Sections that require reading AGENTS.md or README to make sense — context offloaded.
- Trigger phrases buried inside paragraphs instead of surfaced as scannable bullets.
