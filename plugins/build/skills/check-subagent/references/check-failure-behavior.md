---
name: Failure Behavior
description: The body names how the agent handles bad input, missing access, and ambiguous requests, with deterministic exits and explicit reporting to the parent.
paths:
  - "**/.claude/agents/**/*.md"
  - "**/agents/**/*.md"
---

State how the agent behaves on blockers — bad input, missing access, ambiguous request — with deterministic exits and explicit reporting to the parent.

**Why:** Deterministic exits prevent loops, hallucinated workarounds, and unsafe flailing. Agents that authorize open-ended recovery ("try other approaches until something works") are the documented top cognitive fault in multi-agent systems — they improvise into unsafe actions when blocked. The parent needs to know what failure looks like coming back, not infer it from a half-finished result. Source principle: *Explicit failure behavior.*

**How to apply:** Add a `## Failure behavior` section (or equivalent) naming how the agent handles bad input, missing access, and ambiguous requests. Specify deterministic exits — no "try other approaches until something works." State what the agent reports to the parent on failure.

```markdown
## Failure behavior

- If a file cannot be read, emit `{file, error: "<reason>"}` and continue.
- If the required tool is unavailable, report the blocker to the parent and stop.
- If the request is ambiguous, ask one clarifying question; if no answer, stop.
```

**Common fail signals (audit guidance):**
- No Failure / Errors / Exceptions / On-blocker section (or equivalent).
- The section exists but describes only the happy path.
- Instructions authorize open-ended recovery ("try other approaches until something works").
- No statement of what the agent reports to the parent on failure.
