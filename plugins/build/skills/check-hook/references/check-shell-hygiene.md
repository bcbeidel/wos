---
name: Shell Hygiene
description: Hook shell scripts use the safety preamble, route output correctly, and follow portable conventions.
paths:
  - "**/.claude/hooks/**/*.sh"
  - "**/.claude/hooks/**/*.bash"
  - "**/.claude/hooks/**/*.py"
---

Start hook shell scripts with `#!/usr/bin/env bash` + `set -Eeuo pipefail`, guard detection commands that legitimately exit non-zero, route errors to stderr, prefer `[[` over `[`, and never commit `set -x`.

**Why:** Without `set -Eeuo pipefail`, shell hides failures: an undefined variable expands to empty, a failing pipeline stage silently succeeds, and partial outputs corrupt downstream logic. Detection commands (`grep`, `diff`, `test`, `[`) that legitimately exit non-zero will trip `-e` and abort the script prematurely — the hook returns a false-positive "block" on the way out. Errors written to stdout on a blocking exit are discarded (Claude only parses stdout on exit 0); the user sees nothing. `[` lacks `[[`'s safer parsing of empty values and globbing. A committed `set -x` floods stderr and leaks payload values into transcripts. Severity: `warn`.

**How to apply:** start every hook shell script with the bash shebang and the safety preamble. Wrap any `grep`/`diff`/`test` whose non-zero exit is meaningful in `if`, or trail it with `|| true`. Use `>&2` for all error and log output. Use `[[` for conditionals. Remove any committed `set -x`.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

INPUT=$(cat)

# Detection with expected non-zero
if grep -q "pattern" "$FILE"; then ...; fi
# Or
grep -q "pattern" "$FILE" || true

# Errors to stderr
echo "blocked: ${reason}" >&2
exit 2

# [[ over [
if [[ "$VAR" == "value" ]]; then ...; fi
```

**Common fail signals (audit guidance):**
- Missing `set -Eeuo pipefail` (or only a partial subset like `set -e`).
- `#!/bin/bash` shebang instead of `#!/usr/bin/env bash`.
- Bare `grep`/`diff`/`test` on a line of its own (not in `if`, no `|| true`) — first false negative aborts the script.
- `echo "error: ..."` without `>&2`.
- Single-bracket `[ ... ]` conditionals in a `.sh`/`.bash` hook.
- Committed `set -x` (uncommented).
