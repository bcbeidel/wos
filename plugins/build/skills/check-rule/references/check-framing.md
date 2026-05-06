---
name: Framing
description: State rules positively — name the target action; pair prohibitions with their positive alternative.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

State the rule as a positive action that names the target. When a prohibition is unavoidable, pair it with the positive alternative ("Use X; never use Y").

**Why:** Negations are linguistically fragile — a dropped or misattributed `not`/`don't`/`never` inverts the rule, and Claude (or a human reader) ends up doing the opposite of the intent. Pure prohibitions also leave the target action implicit; the reader knows what to avoid but not what to reach for instead, producing inconsistent adherence even when the negation survives.

**How to apply:** Restate "Don't X" as the positive directive that replaces it. If the rule has no clean positive counterpart (e.g., "Never log PII"), the prohibition is load-bearing and stands. Rewrite stacked negations ("Don't forget to not return null") with at most one negation. Replace hedged prohibitions ("Try not to …", "Avoid when possible") with a committed directive plus a named exception, since hedged prohibitions are vague *and* negative.

```markdown
Thread dependencies through constructors; never reach for module-level globals.
```

**Common fail signals (audit guidance):**
- Rule statement is only a prohibition ("Don't use global state", "Never commit secrets") with no positive counterpart stated
- Multiple negations stacked in a single sentence ("Don't not return …")
- Hedged prohibitions ("Try not to …", "Avoid when possible") — vague *and* negative

**Exception:** When the negation is load-bearing and no clean positive counterpart exists (e.g., "Never log PII", "Never commit secrets"), the prohibition stands as written and any WARN is a false positive.
