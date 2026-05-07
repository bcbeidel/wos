---
name: Output Contract
description: Output format is mandated explicitly (JSON schema, named markdown structure, specific artifact path), and ambiguous tasks carry one concrete realistic example.
paths:
  - "**/.claude/agents/**/*.md"
  - "**/agents/**/*.md"
---

**Why:** Downstream callers parse the response. Free-form prose output forces every consumer to write its own parser — and drifts silently when the agent's phrasing changes. A concrete input/output example at the point of maximum ambiguity removes interpretive ambiguity the prose alone cannot. Synthetic placeholders (`<placeholder>`, `foo`, `bar`) do not pin behavior the way a realistic case does. Source principles: *Output format is explicit.* *One concrete example when the task is ambiguous.*

**How to apply:** Name the output format explicitly — JSON schema, named markdown structure, or artifact path. For ambiguous tasks (multiple reasonable output shapes exist), add one realistic input/output example with real-looking values.

```markdown
## Output

Return findings as JSON: `[{file: string, line: int, rule: string, message: string}]`.
Example: `[{file: 'src/foo.ts', line: 12, rule: 'no-unused-vars', message: "'bar' is defined but never used"}]`.
```

**Common fail signals (audit guidance):**
- Body mentions "report findings" or "return results" without naming the format.
- Format is named but the structure is not described (no field list, no schema reference, no example).
- Task is ambiguous (multiple reasonable output shapes exist) and no example is supplied.
- Example supplied is synthetic (`<placeholder>`, `foo`, `bar`) rather than a realistic case.
