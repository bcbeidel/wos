---
name: Error Handling & Messaging
description: Local hook scripts must use strict mode, emit actionable failure messages (file/line/fix), and document any linter-rule disables in args.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

**Why:** Actionable messages distinguish a working gate from a noisy one — *Shell hooks must start with strict mode*, *Failure messages must be actionable*, *Exit non-zero on failure*. A hook that prints `failed` and exits 1 forces the developer to re-run with `-v` (or worse, `--no-verify`) to diagnose; an undocumented `--ignore E501,W291,E402` makes the next reader wonder whether the rule was a deliberate exception or carelessly silenced. Noisy gates get bypassed; opaque disables become permanent.

**How to apply:** For every local script, confirm `set -Eeuo pipefail` plus a safe `IFS=$'\n\t'` (shell) or equivalent strict patterns (Python `if __name__ == "__main__"` + non-zero exits). Confirm every error branch prints file / line / fix to stderr. Confirm any linter-disable arg (`--ignore=...`, `--no-strict`, `--exit-zero`) is paired with an inline comment explaining why those rules are off for this codebase.

```yaml
      - id: black
        name: format python with black
        args: [--safe]
        require_serial: true
        # --skip-string-normalization removed: string-style consistency wanted
```

```bash
printf 'error: %s:%d: %s (fix: %s)\n' "$file" "$lineno" "$msg" "$fix" >&2
exit 1
```

**Common fail signals (audit guidance):** A local script that `exit 1`s with no message on mismatch; `ruff --ignore=E501,W291,E402` with no comment explaining why those rules are off for this codebase.
