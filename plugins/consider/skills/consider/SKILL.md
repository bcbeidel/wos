---
name: consider
description: Apply structured mental models to think through problems. Use when the user wants to "analyze", "evaluate", "think through", "decide between", "weigh tradeoffs", or needs a framework for a decision.
argument-hint: "{model-name} [topic to analyze]"
user-invocable: true
license: MIT
---

Apply structured mental models to problems. If a specific model was requested,
invoke the matching `/consider:{model-name}` command. If no model was specified,
help the user choose by presenting the options below.

## Available Models

Each model invokes as `/consider:<model-name>` — see the marketplace listing or `plugins/consider/skills/` for the full set.

## Usage

```
/consider:first-principles how to design a caching system
/consider:inversion how to make our product successful
/consider:pareto where to focus testing effort
```

If no model is specified, ask the user what they want to think through, then
suggest 2-3 models that would be most relevant to their problem.

## Key Instructions

- When no model is specified and the user's problem is unclear, ask one clarifying question before suggesting models.

## Anti-Pattern Guards

1. **Suggesting too many models** — presenting more than 2–3 options when no model is specified overwhelms rather than guides; curate to the best fit.
2. **Routing non-analytical tasks here** — this skill applies mental models, not implementation, debugging, or research; route those elsewhere.

## Handoff

**Chainable to:** Any `/consider:{model-name}` sub-skill
