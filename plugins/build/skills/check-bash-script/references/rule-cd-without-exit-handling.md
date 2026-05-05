---
name: Guard cd With Exit Handling
description: Guard `cd` with `|| exit` (or `|| return` inside a function), or rely on `set -e`. A failed `cd` followed by destructive operations targets the wrong directory (shellcheck SC2164).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Guard `cd` with `|| exit` (or `|| return` inside a function); never run destructive operations after a `cd` that may have silently failed.

**Why:** a failed `cd` (target doesn't exist, permission denied, target is a regular file) leaves the process in its original directory. The next line — `rm -rf *` or `mv ./* /elsewhere/` — operates on the original directory, not the intended target. This is the destroyed-systems pattern: a script meant to clean a build subdirectory wipes the user's home directory because the build directory didn't exist this run. The fix is one character of insurance: `cd "$dir" || exit` aborts the script if `cd` fails, ensuring downstream operations never run in the wrong directory.

**How to apply:** add `|| exit` to every `cd` at the script's top level. Inside a function, use `|| return 1` so the failure propagates. When the script has `set -e` enabled and the failing `cd` is unambiguously fatal, `set -e` covers this case — but explicit guards read more clearly and survive future refactors that might disable `set -e` in subshells.

```bash
# Before — destroyed-systems pattern
cd /some/dir
rm -rf *

# After — explicit guard
cd /some/dir || exit
rm -rf *

# After — function variant
cleanup_dir() {
  cd "$1" || return 1
  rm -rf ./*
}
```

**Exception:** when `set -e` is active AND the script doesn't subshell around the `cd`, `set -e` triggers on the failed `cd`. The explicit guard is preferred because it documents the safety intent at the call site rather than relying on a global mode the reader has to remember.
