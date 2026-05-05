---
name: Mktemp Trap Pairing
description: Register a cleanup `trap` immediately after every `mktemp` invocation so temp state is removed on any exit, including signals.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Register a cleanup `trap` immediately after every `mktemp` invocation (or before, when feasible) so temp state is removed on any exit — including signals and unhandled errors.

**Why:** without the trap, the temp directory leaks on any non-zero exit, including signals (Ctrl-C, SIGTERM from a supervisor, an OOM kill). Disk fills up over time as failed runs accumulate; subsequent runs collide on predictable-prefix names; debugging gets harder because the next operator can't tell which temp dirs are "in use" vs. orphaned. The pairing is mechanical and trivial — it's the absence of the trap, not the cost of adding it, that's the cost.

**How to apply:** capture the temp path in a variable, then register the trap on the next line. Use `EXIT INT TERM` so the cleanup runs on normal exit, Ctrl-C, and supervisor termination. Quote the path in the trap's command to handle paths with spaces. If the script creates multiple temp paths, use a single trap with all paths in the cleanup command.

```bash
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT INT TERM
do_work "$tmpdir"
```

```bash
# Multiple temp paths, single trap
tmpdir="$(mktemp -d)"
tmpfile="$(mktemp)"
trap 'rm -rf "$tmpdir" "$tmpfile"' EXIT INT TERM
```

**Exception:** none in scope. Even "this temp dir will be cleaned up at the end of the script" doesn't excuse a missing trap — the script may exit early on error, signal, or `set -e` trigger before reaching the cleanup.
