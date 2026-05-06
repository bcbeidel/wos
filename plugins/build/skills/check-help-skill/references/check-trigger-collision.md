---
name: Trigger Collision
description: The help-skill's `description` does not collide with sibling-skill triggers — neither identical phrasing nor heavy token overlap.
paths:
  - "**/skills/help/SKILL.md"
---

Compare the help-skill's `description` against every sibling's `description` and ensure their trigger sets are disjoint.

**Why:** The router cannot disambiguate two skills that match the same trigger — it picks one arbitrarily, and the user gets unpredictable routing. A help-skill in isolation can pass every other dimension cleanly while being fundamentally broken: when the router is presented with the help-skill alongside its siblings, it cannot pick correctly. This is the load-bearing cross-entity check. Skipping it leaves the highest-value defect undetected — the help-skill silently steals routing from siblings (or vice versa) on every meta-shaped query, and the user never sees the collision because the router just dispatches *something*.

**How to apply:** For every sibling skill in the plugin, tokenize both descriptions (verbs + nouns from "Use when…" clauses) and compare. Two heuristics, two severities:

- **Identical trigger phrasing** — both descriptions contain the same exact trigger phrase (e.g., both fire on "list skills"). Severity: `warn`.
- **Token overlap** — shared trigger-phrase tokens exceed a threshold. 3+ shared tokens: `info`. 5+ shared tokens: `warn`.

For each collision, surface both descriptions and the shared tokens. The auditor does not pick a winner — the user resolves by narrowing either side. The help-skill is usually the one to narrow because its distinct value is meta-trigger; siblings own their workflow triggers.

```yaml
# Collision (WARN) — both fire on "build a skill"
help.description: Use when the user wants to use the build plugin to build a skill.
build-skill.description: Use when the user wants to build, scaffold, or create a skill.

# Resolved — help narrowed to meta-questions
help.description: Use when the caller asks "what's in the build plugin" or "list build skills".
build-skill.description: <unchanged>
```

**Common fail signals (audit guidance):**
- Identical trigger phrase appearing in both help and a sibling description (`warn`).
- 5+ shared verbs/nouns from "Use when…" clauses across help and any sibling (`warn`).
- 3+ shared trigger tokens but not 5+ (`info` — coaching signal, surface but do not block).
- Help-skill description uses sibling skill verbs ("build", "audit", "scope") as primary triggers.
- Help-skill claims the plugin's whole domain ("use the X plugin"); sibling claims a slice — heavy overlap by construction.
