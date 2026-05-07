---
name: Example Realism
description: Use real codebase identifiers in examples — table names, function names, module paths a reader would recognize. Synthetic placeholders weaken the rule.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

When examples are present, use real identifiers from the codebase — actual table names, function names, module paths a reader would recognize. An optional file-path comment showing provenance strengthens the example.

**Why:** Domain-specific identifiers anchor the rule more strongly than synthetic placeholders. The evaluator (human or Claude) recognizes the context and applies the rule the way they would to new code in the same codebase. Synthetic identifiers (`foo`, `bar`, `baz`, `myFunction`, `Thing`, `Widget`, `placeholder`, `example_*`) make the example look invented rather than sourced — the reader can't pattern-match against real code, and the rule reads as advisory rather than load-bearing. Evidence-anchored rubrics produce more reliable judgments than inference-only rubrics.

**How to apply:** Replace placeholders with real code from the codebase. If the rule is about API handlers, lift an actual handler function; if it's about staging models, name an actual table. A file-path comment (`// src/api/handlers/users.ts`) is optional but a strong provenance signal. When no real example exists yet because the rule is about a new convention, name a future-state identifier that matches the codebase's vocabulary rather than reaching for `foo`. This dimension applies only when the rule contains at least one code block; rules with no examples return N/A.

```typescript
// src/api/handlers/users.ts
async function getUser(userId: string) {
  return db.users.findById(userId);
}
```

**Common fail signals (audit guidance):**
- Examples use generic placeholders (`foo`, `bar`, `baz`, `myFunction`, `Thing`, `Widget`) as primary identifiers
- Code looks synthesized rather than sourced (no domain context, generic variable names, no recognizable module boundaries)
