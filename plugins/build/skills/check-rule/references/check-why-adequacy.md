---
name: Why Adequacy
description: Include the reasoning — for judgment-based rules, name the failure cost and at least one legitimate exception.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

Include reasoning for every rule. For judgment-based rules — those signaled by compliant/non-compliant examples, `violation`/`exception`/`failure` vocabulary, or multi-paragraph why prose — name the specific failure cost (what breaks, who bears it) and at least one legitimate exception.

**Why:** Without reasoning, Claude can't extend the rule to edge cases and maintainers can't decide whether the rule is still load-bearing. Rules without failure cost get weighed as bureaucratic overhead rather than real risk — disable rates rise. Rules with no named exception appear to admit no flexibility, causing developers to disable them entirely rather than follow them in the 95% case. The exception clause is what keeps the rule alive when the edge case finally arrives.

**How to apply:** For simple directive rules ("Use snake_case for table names"), a brief inline `**Why:**` line suffices. For judgment-based rules, the why must do two things: name the specific consequence and who bears it (not just "X is bad"), and append an `Exception:` line naming at least one legitimate bypass case. Replace "It creates noise" with "exposes internal state via browser developer tools and adds measurable latency in high-frequency call paths." Replace silence on exceptions with "Exception: test files; scripts in `tools/` that are never bundled for production."

```markdown
Use snake_case for Postgres table names.

**Why:** case-sensitive identifiers in Postgres require quoting; snake_case avoids the quoting trap across ORMs.
```

**Common fail signals (audit guidance):**
- No why/reasoning at all (no `**Why:**` line or `## Why` section, no rationale in prose)
- Judgment-based rule's why names the violation only ("X is bad") with no specific failure cost
- Judgment-based rule has no exception policy — rules that admit no exception get disabled wholesale when the edge case arrives

**Exception:** Simple directive rules ("Use snake_case for table names") need only a brief inline why — failure cost and exception clause are required only when the rule is judgment-based.
