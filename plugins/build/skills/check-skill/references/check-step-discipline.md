---
name: Step Discipline
description: Each `## Steps` item is one atomic imperative action — no rationale, no fused actions, no nesting beyond two levels.
paths:
  - "**/SKILL.md"
---

Write Steps as a numbered sequence of atomic imperative actions — one verb per step, addressed to the agent, free of embedded rationale, with conditional branches at most two levels deep.

**Why:** Atomic imperative steps are followed reliably; commentary and fused actions degrade instruction-following. When rationale ("we do this because…") lives inside a step body, the agent has to separate the action from its justification on every read — slower and less reliable than putting rationale in surrounding prose. Multi-action fused steps ("read the file, validate it, write output") collapse three checkpoints into one, hiding partial progress. Conditional nesting beyond two levels signals the workflow has split into a different skill that should be extracted.

**How to apply:** Rewrite each step to start with an imperative verb addressed to the agent ("Run `foo`", "Read `$ARGUMENTS`"). Move rationale to the surrounding prose. Split fused steps into separate items. When conditional logic exceeds two levels, extract the deeper branch into a sibling skill rather than nesting further. Keep step paragraphs to two sentences or fewer.

```markdown
1. Read `$ARGUMENTS`.
2. Validate the input's schema against the registry.
3. If the schema is not cached, cache it. If the cache is stale, refresh it.
4. Write the Parquet output to `./output.parquet`.
```

**Common fail signals (audit guidance):**
- Steps in passive voice or describing what "should happen" rather than telling the agent what to do
- Reasoning or rationale embedded inside a step body ("We do this because …") — reasoning belongs in surrounding prose
- Conditional logic nested more than two levels deep ("if A: if B: if C: …")
- Multiple distinct actions fused into one step with "and" or bullet sub-lists
- Step paragraphs longer than two sentences
