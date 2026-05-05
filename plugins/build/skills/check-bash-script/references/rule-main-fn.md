---
name: Main Function
description: Wrap top-level execution logic in a `main` function so the script is sourceable and has a single entry point a reader can find immediately.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Wrap top-level execution logic in a `main` function rather than running statements at the script's top level.

**Why:** a `main` function makes the script sourceable for testing — `bats` and `shunit2` and ad-hoc `source ./script.sh` can load helper functions without running the full script as a side effect. It also gives a reader a single entry point: a fresh contributor opening the file knows to look for `main` to understand the script's flow, rather than tracing top-to-bottom through interleaved variable definitions and execution. The pattern composes with the sourceable guard rule (`rule-main-guard.md`) — guard at the bottom invokes `main "$@"` only when run directly.

**How to apply:** wrap top-level execution in `main() { ... }`. Pass arguments through with `main "$@"` at the end of the file. Use `local` for variables inside `main` so they don't pollute the caller's namespace when sourced. Use `${1:?usage: ...}` for required positional arguments to fail fast with a clear message.

```bash
#!/usr/bin/env bash
set -euo pipefail

main() {
  local input="${1:?usage: script <input>}"
  local output="${2:-/dev/stdout}"
  process "$input" > "$output"
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
```

**Exception:** scripts that are intentionally non-sourceable single-purpose snippets (e.g., a one-off migration script that should not be re-runnable as a function library). These are rare; document the choice in the header. The audit emits WARN — judgment-level coaching, not blocking.
