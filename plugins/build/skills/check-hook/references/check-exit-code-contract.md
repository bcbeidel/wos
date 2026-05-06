---
name: Exit Code Contract
description: Command hooks signal pass/warn/block through the correct exit code, and Python hooks handle exceptions explicitly.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Use exit 2 for blocking paths, exit 1 for warn paths, exit 0 for pass — and in Python, call `sys.exit(2)` explicitly inside every exception handler that should block.

**Why:** `exit 1` is non-blocking — Claude shows the error in the transcript and proceeds anyway. A blocking hook that exits 1 looks like it works (the message is visible) but never actually stops the tool call. Python uncaught exceptions exit 1 by default, so a hook that catches nothing silently downgrades every blocking path to a warning. Both failures are silent — the gate looks installed but lets traffic through. Severity: `fail`.

**How to apply:** every blocking branch ends with `exit 2` (bash) or `sys.exit(2)` (Python). Wrap Python hook bodies in `try/except` and call `sys.exit(2)` from the handler — never rely on uncaught exception fall-through. Reserve `exit 1` for warn-only paths the user is meant to see but not be blocked by. `exit 0` for pass.

```bash
# Bash blocking path
echo "blocked: ${reason}" >&2
exit 2
```

```python
# Python blocking path, including in handlers
try:
    enforce(payload)
except Exception as e:
    print(f"blocked: {e}", file=sys.stderr)
    sys.exit(2)
```

**Common fail signals (audit guidance):**
- Bash hook with blocking prose (`echo "blocked"`, `echo "rejected"`) followed by `exit 1` — silently non-blocking.
- Python hook body with no top-level `try/except` and no explicit `sys.exit(2)` — exceptions fall through to exit 1.
- Bash hook with bare `exit` (no code) on a blocking path — defaults to last command's exit status.
- Python hook that raises to signal blocking (`raise RuntimeError(...)`) — exits 1, not 2.
