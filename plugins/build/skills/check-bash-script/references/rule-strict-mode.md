---
name: Strict Mode
description: Bash scripts must enable strict-mode error handling via `set -euo pipefail` in the prologue, immediately after the shebang and header comment.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Enable strict-mode error handling with `set -euo pipefail` immediately after the shebang and header comment, before any executable code.

**Why:** strict mode turns silent failures, unset-variable typos, and mid-pipeline errors into loud, early exits. Without it, a typo in `$user_imput` silently expands to empty and downstream code processes garbage; a failing pipeline stage's exit code is hidden by the last stage's success; and a missing required file is read as zero bytes without a peep. Three flags do three independent jobs: `-e` exits on any unhandled error, `-u` errors on unbound variable references, and `-o pipefail` propagates pipe failures so `bad | good` exits non-zero.

**How to apply:** insert `set -euo pipefail` as the first executable line, after the shebang line and any leading comment block. The three-flag form is canonical; equivalent three separate `set` lines (`set -e; set -u; set -o pipefail`) are accepted but offer no advantage. Use `set -Eeuo pipefail` (capital `E`) when also installing an ERR trap, so traps inherit through functions, command substitutions, and subshells.

```bash
#!/usr/bin/env bash
# rotate-logs — Compress logs older than 30 days.

set -euo pipefail

main() {
  local log_dir="${1:?usage: rotate-logs <log-dir>}"
  ...
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
```

**Exception:** scripts that need to inspect command exit codes inline can wrap the inspection block with `set +e; cmd; rc=$?; set -e`. Use sparingly — most cases are better solved with `if cmd; then ... fi` or `cmd || handle_failure`. The exception is documented per-block (a comment explaining why), not per-script.
