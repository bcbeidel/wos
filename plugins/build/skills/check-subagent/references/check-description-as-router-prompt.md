---
name: Description as Router Prompt
description: The `description` is a routing instruction for the main agent — verb-led capability, trigger conditions, at least one exclusion, and what the agent returns.
paths:
  - "**/.claude/agents/**/*.md"
  - "**/agents/**/*.md"
---

**Why:** The main agent uses the `description` to decide whether to delegate. A capability summary ("Agent that handles TypeScript work") gives the router nothing to classify against; a verb-led routing rule with explicit triggers and exclusions does. Proactive subagents need explicit routing language ("use proactively") or the router will not self-invoke them. Source principle: *Description is a router prompt, not human documentation.*

**How to apply:** Rewrite the description with four elements: verb-phrase capability, trigger conditions (when to invoke), at least one exclusion (when NOT to invoke), and the returned output (format, location, artifact). Add "use proactively" or equivalent if the agent should self-invoke without explicit user request.

```yaml
description: Lints staged TypeScript files and returns findings as JSON. Use after editing `.ts` or `.tsx` files when checking lint status before commit. Not for JavaScript files or type errors.
```

**Common fail signals (audit guidance):**
- Opens with a noun phrase ("Agent that handles…") or a capability summary ("Helper for data tasks") rather than a verb-led action.
- No trigger conditions — nothing tells the router *when* to pick this agent.
- No exclusion — nothing distinguishes it from adjacent routing targets.
- No statement of what the agent returns (format, location, artifact).
- Agent is intended for proactive use but no routing language signals this.
