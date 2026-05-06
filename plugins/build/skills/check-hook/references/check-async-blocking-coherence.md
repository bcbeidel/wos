---
name: Async / Blocking Coherence
description: Blocking intent and `async: true` do not coexist in the same hook entry.
paths:
  - "**/.claude/settings.json"
  - "**/.claude/settings.local.json"
---

Either keep the hook synchronous (default, can block) or mark it async (cannot block) — never combine `async: true` with blocking paths or blocking prose.

**Why:** Async hooks run after tool execution regardless of exit code — `exit 2` from an async hook does nothing. A hook described in comments as a "gate" or "blocker" but registered with `"async": true` is theater: the path the script claims to enforce never actually fires. The contradiction is silent — the hook loads, runs, and reports correctly, but the tool call has already completed. Severity: `fail`.

**How to apply:** if blocking is required, omit `async` (synchronous is the default) and ensure blocking paths exit 2. If the hook is genuinely non-blocking — observability, logging, indexing — remove all `exit 2` paths and any "block"/"reject"/"gate" prose. Don't compromise: pick one posture per hook entry.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard.sh"}
        ]
      }
    ]
  }
}
```

**Common fail signals (audit guidance):**
- `"async": true` on the hook entry combined with `exit 2` paths in the referenced script.
- Hook description / comment uses verbs like "block", "reject", "gate", "prevent" while the entry sets `async: true`.
- `"async": true` on a PreToolUse hook (PreToolUse's value is mostly its blocking ability).
- Hook that emits structured `updatedInput` JSON while marked async — async results are ignored for input rewriting.
