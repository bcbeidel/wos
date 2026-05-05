---
name: Subprocess and Tool Hygiene
description: Preflight required external commands, register cleanup traps for created state, and declare or avoid GNU-specific flags in the header.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Preflight required external commands at the top of `main`, register `trap` cleanup for created state, and declare GNU-coreutils dependency in the header when GNU-specific flags are used.

**Why:** failing fast with an actionable message ("missing required commands: jq") beats failing mid-run with a cryptic "command not found: jq" deep in the script's logic. Preflight catches missing dependencies before any work happens — the user knows exactly what to install before the script does anything destructive. `trap` registration before creating state (temp directories, lock files, network connections) ensures cleanup runs on every exit path, including signals; without it, `set -e` exits leave orphaned state that leaks across runs. GNU-flag declaration in the header documents the platform contract — a reader sees the script depends on GNU coreutils and either runs it on Linux or installs `gnu-coreutils` on macOS.

**How to apply:** define a `preflight` function at the top of `main` that checks `command -v <cmd>` for every external dependency. Register `trap 'cleanup' EXIT INT TERM` before the first `mktemp` or `mkdir -p` or connection-open. When using GNU-specific flags (`sed -i`, `grep -P`, `readlink -f`, `date -d`), document the dependency in the header comment.

```bash
#!/usr/bin/env bash
# rotate-logs — Compress logs older than 30 days.
# Dependencies: gzip, find, gnu-coreutils (sed -i)

set -euo pipefail

readonly REQUIRED_CMDS=(jq curl gzip find)

preflight() {
  local cmd missing=()
  for cmd in "${REQUIRED_CMDS[@]}"; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  [[ "${#missing[@]}" -eq 0 ]] || die "missing required commands: ${missing[*]}"
}

main() {
  preflight

  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT INT TERM

  do_work "$tmpdir"
}
```

**Common fail signals (audit guidance):**
- A script that calls `jq` (or `curl`, `aws`, `kubectl`) deep in the logic with no preflight — failure surfaces at the wrong layer.
- `mktemp -d` with no trap — temp directory leaks on any non-zero exit.
- `sed -i 's/.../.../'` with no header dependency declaration — silent macOS/Linux divergence.
- A trap that's registered AFTER the first `mktemp` — failure between `mktemp` and `trap` leaves orphaned state.
- Multiple temp paths created throughout the script with no cleanup tracking — partial-leak hazard.

**Exception:** trivially short scripts (under ~20 lines) using only built-in commands may skip preflight — there's nothing to verify. The audit's judgment surfaces preflight when the script has external dependencies; trivial scripts return PASS silently.
