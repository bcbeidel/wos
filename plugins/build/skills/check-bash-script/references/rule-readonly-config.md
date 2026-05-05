---
name: Readonly Configuration Constants
description: Declare top-level non-trivial constants with `readonly` so accidental reassignment is a hard error and the value's role (configuration, not state) is explicit.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Declare top-level non-trivial configuration constants with `readonly` so accidental reassignment is a hard error and the value's role — configuration, not state — is visually explicit.

**Why:** `readonly` makes accidental reassignment a hard error rather than a silent overwrite. In a 200-line script, a typo five hundred edits later (`TIMEOUT=$user_input` where `TIMEOUT` was meant to stay at 30) silently breaks the configuration; with `readonly`, bash refuses the assignment and the script fails loudly. The visual signal is also load-bearing: a reader scanning the top of the file sees `readonly TIMEOUT=30` and immediately knows "this is configuration, not a variable I should track" — reducing the cognitive load of understanding the script's state.

**How to apply:** prefix top-level non-trivial constants with `readonly`. Apply to API keys, configuration values, paths, and other intentionally-fixed values. Skip ephemeral state and loop counters (those aren't constants). When a constant comes from an environment variable, combine with the `${VAR:?...}` pattern: `readonly API_KEY="${OPENAI_API_KEY:?required}"`.

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly TIMEOUT=30
readonly MAX_RETRIES=3
readonly LOG_DIR="${LOG_DIR:-/var/log/myapp}"
readonly API_KEY="${OPENAI_API_KEY:?OPENAI_API_KEY env var required}"

main() {
  ...
}
```

**Exception:** values that are intentionally re-assigned during script execution (counters, accumulators, mutable state) are not constants — leave them off `readonly`. The audit only flags top-level non-trivial assignments; loop iterators and similar are not in scope.
