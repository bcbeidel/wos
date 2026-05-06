---
name: Stdin Consumption
description: Command hooks consume stdin before the pipe buffer saturates, and the script file is executable.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Drain stdin into a variable at or near the top of the hook, and ensure the script has the execute bit set.

**Why:** Hooks that do not drain stdin hang when the payload exceeds the OS pipe buffer (typically 64 KB on Linux, smaller elsewhere). Large tool payloads — long Bash commands, big file writes, full file reads — silently freeze the session. Non-executable scripts fail indistinguishably from an unloaded hook: no error, no log, just nothing. Both failures are intermittent (small payloads work, large ones don't) which makes them hard to reproduce. Severity: `warn`.

**How to apply:** read stdin with `INPUT=$(cat)` (bash) or `payload = json.load(sys.stdin)` (Python) immediately after the safety preamble. Run `chmod +x .claude/hooks/<name>.sh` on every hook script and commit the executable bit. CI should reject hooks added without it.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

INPUT=$(cat)
# ... rest of hook uses "$INPUT"
```

**Common fail signals (audit guidance):**
- Script body references `tool_input` / `command` / payload fields without first reading stdin — payload empty when matcher fires on large input.
- File at `.claude/hooks/*.sh` without the executable bit (filemode `0644` instead of `0755`).
- Stdin read placed deep in the script, after slow setup — buffer can saturate before the read.
- Python hook calls `sys.stdin.read()` only inside one branch — other branches leak the pipe.
