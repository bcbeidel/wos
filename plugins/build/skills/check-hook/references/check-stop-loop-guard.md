---
name: Stop Loop Guard
description: Blocking Stop and SubagentStop hooks have a re-entry guard that breaks infinite loops.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Add a re-entry guard at the top of every blocking Stop or SubagentStop hook — short-circuit to `exit 0` when the guard fires.

**Why:** A blocking Stop or SubagentStop hook with no guard creates an infinite loop: the hook exits 2, Claude tries to stop again, the hook blocks again, and the only recovery is killing the session. The user loses in-progress context and any unsaved transcript state. SubagentStop receives `stop_hook_active` in its payload — a built-in signal that the runtime is already retrying — but Stop does not, so a session-scoped guard (e.g., a temp file keyed to `session_id`) is required for Stop hooks. Severity: `fail`.

**How to apply:** for SubagentStop, exit 0 immediately when `stop_hook_active == true`. For Stop, write a session-scoped guard file on first invocation and exit 0 if it already exists. For production gates, layer all three: `stop_hook_active` + `last_assistant_message` progress check + session-scoped guard.

```bash
# SubagentStop
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
[[ "$STOP_ACTIVE" == "true" ]] && exit 0
```

```bash
# Stop (stop_hook_active absent)
SESSION=$(echo "$INPUT" | jq -r '.session_id')
GUARD="/tmp/claude-stop-guard-${SESSION}"
[[ -f "$GUARD" ]] && exit 0
touch "$GUARD"
```

**Common fail signals (audit guidance):**
- Hook registered under `Stop` or `SubagentStop` with `exit 2` paths and no guard at the top.
- SubagentStop hook that does not read `.stop_hook_active`.
- Stop hook that relies on `stop_hook_active` (absent from Stop payload) — fails open every time.
- Guard placed after expensive work — the loop still spins doing the work each iteration.
