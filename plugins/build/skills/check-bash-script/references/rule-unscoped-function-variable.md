---
name: Local Declaration Before Assignment
description: Split `local var=$(cmd)` into `local var; var="$(cmd)"` so the substitution's exit status is preserved under strict mode (shellcheck SC2155).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Split `local var=$(cmd)` into a separate `local` declaration plus an assignment so the substitution's exit status is preserved.

**Why:** `local var=$(cmd)` masks `cmd`'s return code because `local` itself returns 0. Under `set -e`, a failing `cmd` should abort the script — but the `local var=...` invocation succeeds (because `local` succeeded), so `set -e` doesn't fire and the script continues with whatever `cmd` produced (often an empty string or a partial output). Splitting the declaration restores the substitution's exit status: `local var; var="$(cmd)"` makes `var="$(cmd)"` a standalone command whose exit status is `cmd`'s, so `set -e` correctly triggers on failure. The bug is silent — scripts with this pattern look fine until `cmd` fails for the first time and the error goes unnoticed.

**How to apply:** when a function-local variable is initialized from a command substitution, separate the `local` declaration from the assignment.

```bash
# Before — return status of some_cmd is masked
some_function() {
  local result=$(some_cmd)
  process "$result"
}
```

```bash
# After — set -e correctly fires if some_cmd fails
some_function() {
  local result
  result="$(some_cmd)"
  process "$result"
}
```

**Exception:** `local` initializations from literal values or simple expansions (not command substitutions) are not affected — `local count=0` and `local path="$1"` are fine. The rule applies specifically when the right-hand side is `$(...)` or backticks, where the substitution's exit status matters.
