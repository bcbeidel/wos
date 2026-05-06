---
name: Trigger Quality
description: The `description` frontmatter fires on meta-questions about the plugin (what's in it, list its skills, which fits a task), not on the plugin's own workflows.
paths:
  - "**/skills/help/SKILL.md"
---

Shape the `description` so it retrieves on meta-questions about the plugin, not on tasks the plugin's siblings perform.

**Why:** A description shaped like "Use when the user wants to use the X plugin's features" is too generic and competes with siblings — the router sees the help-skill claiming territory that `build-skill`, `check-skill`, and the rest already own. When the help-skill matches "build a skill", the router cannot disambiguate between the help-skill (which would orient the user) and `build-skill` (which would actually build one). The help-skill loses its routing edge and ends up firing on workflows it should be deferring to siblings — or worse, never fires because its trigger collides with a sibling and the sibling wins. Lead with the caller's situation; the help-skill's distinct situation is "I want orientation about this plugin", not "I want to do something this plugin does".

**How to apply:** Read the description in isolation and ask: does this fire on meta-questions ("what's in this plugin", "list X skills", "how do I use X", "which X skill fits this task") or on operational tasks ("build a skill", "audit a hook")? Specific meta-trigger phrases pass; generic capability phrasing fails. Lead with "Use when the caller asks…" and embed at least one verbatim meta-question. This dimension judges the description in isolation; the Trigger Collision rule judges it against actual siblings. Severity: `warn`.

```yaml
# Good — specific meta-triggers
description: >-
  Use when the caller asks "what's in the build plugin", "list build
  skills", "how do I use build", or "which build skill fits this task".

# Bad — generic capability phrasing, collides with siblings
description: Use when the user wants to build, audit, or work with Claude Code primitives.
```

**Common fail signals (audit guidance):**
- Description starts with "Use when the user wants to <verb>…" where `<verb>` is a sibling skill's verb.
- No verbatim meta-question phrase ("what's in", "list", "how do I use", "which fits").
- Description claims the plugin's domain at large rather than orientation about it.
- Capability-shaped phrasing ("for X, Y, and Z") instead of situation-shaped phrasing.
- Description is shorter than ~15 words — likely too generic to be specific to meta-questions.
