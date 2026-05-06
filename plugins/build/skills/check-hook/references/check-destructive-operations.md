---
name: Destructive Operations
description: Hook scripts do not execute irreversible commands without explicit user action.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Hooks must never run `rm -rf`, `git reset --hard`, `git checkout .`, `git push --force`, or `git push -f` automatically.

**Why:** Hooks fire automatically on every matched tool call — there is no user confirmation step. An irreversible command in a hook body destroys work the moment a matcher hits, often in the middle of an unrelated operation. `git reset --hard` deletes uncommitted changes; `git push --force` rewrites shared history; `rm -rf` against a payload-derived path can wipe the project. The blast radius is unbounded and the action cannot be undone. Severity: `fail`.

**How to apply:** remove the destructive command. If cleanup is genuinely needed, move it to a user-invoked skill or command (where the user sees and approves the action) or narrow the operation to a specific known-safe target (e.g., `rm -rf "${SPECIFIC_TMPFILE}"` not `rm -rf "$DIR"/*`). Hooks observe and block; they do not mutate destructively.

```bash
# Wrong — destructive in a hook
rm -rf "$WORKDIR"/*

# Right — narrow, known target, on EXIT trap
trap 'rm -f "${TMPFILE:-}"' EXIT
```

**Common fail signals (audit guidance):**
- Literal `rm -rf` anywhere in the hook body, especially with a variable target.
- `git reset --hard`, `git checkout .`, `git checkout -- .`, `git clean -fd` — all destroy uncommitted work.
- `git push --force` or `git push -f` — rewrites shared history.
- `rm` against a path derived from `tool_input` / payload — attacker-controlled deletion target.
- Database `DROP`, `TRUNCATE`, or filesystem `mkfs` / `dd` patterns.
