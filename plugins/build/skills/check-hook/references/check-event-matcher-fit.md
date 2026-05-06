---
name: Event-Matcher Fit
description: Hooks fire on the right lifecycle event for their enforcement goal, and the matcher selects the intended tool invocations with correct syntax.
paths:
  - "**/.claude/settings.json"
  - "**/.claude/settings.local.json"
---

Pair the hook's enforcement goal with a blockable lifecycle event and write the matcher with canonical tool casing and the syntax tier the event accepts.

**Why:** Blocking intent on a non-blockable event (most commonly PostToolUse) means the tool has already run — `exit 2` is ignored and the gate is theatrical. A matcher with lowercase or typo'd tool name silently matches nothing; the hook loads but never fires. Regex syntax inside FileChanged is interpreted as a literal list, so the matcher matches no real path. All three failures look identical at the surface — a hook that "exists" but enforces nothing — and produce silent gaps in coverage. Severity: `fail`.

**How to apply:** route blocking goals (refusals, rewrites, gates) to PreToolUse, UserPromptSubmit, or another blockable event. Use canonical tool casing exactly: `Bash`, `Write`, `Edit`, `MultiEdit`, `Read`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Agent`, `NotebookEdit`, `NotebookRead`. For FileChanged, write the matcher as a literal list (`".envrc|.env"`) — never regex syntax. For regex matchers in tool-name fields, include a non-alphanumeric character (e.g., `"mcp__memory__.*"`) to escape the exact-match tier.

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
- Blocking hook (`exit 2` paths or "block"/"reject" prose) registered under PostToolUse, Notification, or Stop — wrong tier.
- Matcher uses lowercase (`bash`, `write`) or typo (`Edt`, `MultEdit`) — silently matches nothing.
- FileChanged matcher contains regex metacharacters (`.*`, `\.`, `[`) — interpreted as literal list characters.
- Bare alphanumeric matcher intended as regex (e.g., `"mcp_memory"`) — matched at the exact-match tier instead.
