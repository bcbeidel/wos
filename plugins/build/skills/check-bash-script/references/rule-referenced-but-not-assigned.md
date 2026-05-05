---
name: Variable Referenced But Not Assigned
description: Either assign the variable, default it with `${var:-default}`, or fail-fast it with `${var:?message}` — shellcheck flags references with no visible assignment (SC2154).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

When shellcheck flags a variable as referenced but not assigned, either assign it explicitly, default it with `${var:-default}`, or guard it with `${var:?message}` to fail fast.

**Why:** SC2154 catches a likely typo or a forgotten assignment — the script reads `$config_path` but no `config_path=...` exists in the visible scope. Without `set -u`, the reference silently becomes empty; with `set -u`, the script fails at runtime with a generic "unbound variable" error. The fix is to name the intent: either provide a sensible default (the variable is optional), require it from the environment (the variable is configuration), or initialize it in a clear place (the variable is local state). Each path makes the script easier to read and harder to break.

**How to apply:** for required external inputs, use `${var:?message}` so unset triggers an immediate, descriptive failure. For optional inputs with defaults, use `${var:-default}`. For local state, initialize the variable in `main` or its enclosing function before first use. When the reference comes from `set -a` (auto-export) or sourced files, add a `# shellcheck source=...` directive to point shellcheck at the assignment.

```bash
# Before — flagged: $config_path never assigned in this file
process "$config_path"

# After — fail fast if unset
process "${config_path:?config_path required}"

# After — default value
config_path="${config_path:-/etc/myapp/config.yml}"
process "$config_path"

# After — explicit local assignment
local config_path="$1"
process "$config_path"
```

**Exception:** variables assigned in a sourced helper file. Add `# shellcheck source=path/to/helpers.sh` before the `source` line so shellcheck can resolve the assignment. The audit accepts properly-pointed sources; it flags the case where shellcheck genuinely can't see an assignment.
