---
name: Command Path Expansion
description: The `command` field in settings.json uses a path form that resolves reliably across Claude Code versions.
paths:
  - "**/.claude/settings.json"
  - "**/.claude/settings.local.json"
---

Use `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh` (or an absolute path) for hook commands — never `$HOME` or `~`.

**Why:** Tilde and `$HOME` expansion in the `command` field is inconsistent across Claude Code versions: some versions expand them at registration time, some at exec time, some not at all. When expansion fails, the hook silently fails to load — no error appears, the entry just doesn't fire. The behavior depends on the user's installed CLI version, not the project, so the same `settings.json` works for one collaborator and silently breaks for another. Severity: `warn`.

**How to apply:** project-scoped hooks use `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh`. Plugin-scoped hooks use `"$CLAUDE_PLUGIN_ROOT"/...` or `"$CLAUDE_PLUGIN_DATA"/...`. Absolute paths (`/usr/local/bin/...`) are fine when the script lives outside the project. Quote the variable so spaces in the project path don't break the command.

```json
{
  "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/<name>.sh"
}
```

**Common fail signals (audit guidance):**
- `"command": "~/.claude/hooks/..."` — tilde expansion unreliable.
- `"command": "$HOME/.claude/hooks/..."` — `$HOME` expansion unreliable.
- `"command": "$CLAUDE_PROJECT_DIR/.claude/hooks/..."` without surrounding quotes — breaks when the project path contains spaces.
- Relative paths (`.claude/hooks/...`) — resolved against an undefined working directory.
