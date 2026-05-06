---
name: Voice and Framing
description: Instructions are imperative, terminology is consistent, and the body neither hedges nor apologizes.
paths:
  - "**/.claude/agents/**/*.md"
  - "**/agents/**/*.md"
---

Write instructions in imperative mood, lock terminology to one term per concept, and remove hedging or apologetic language.

**Why:** Hedging ("try your best", "if possible", "might want to") licenses mediocre output and weakens the instruction surface — the model reads tentativeness as permission to take shortcuts. Inconsistent terminology (the same concept called "finding" then "issue" then "violation") makes the prompt harder for the model to follow and for reviewers to audit. Source principle: *Direct voice.*

**How to apply:** Rewrite tentative instructions in imperative mood. Remove hedging phrases and apologies. Pick one term per concept and use it consistently across the body. Replace tentative modal constructions ("you should", "you may want to", "consider running") with direct imperatives ("run", "report", "stop").

```markdown
Find lint errors and report them as JSON.
```

**Common fail signals (audit guidance):**
- Hedging phrases: "try your best", "might want to", "if possible", "perhaps", "sorry", "unfortunately".
- Tentative modal verbs where imperative is appropriate ("you should", "you may want to", "consider running" in place of "run").
- The same concept referred to by multiple names across the body (e.g., "finding" vs. "issue" vs. "violation" used interchangeably).
