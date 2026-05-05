---
name: Quote Positional Arguments
description: Use `"$@"` (quoted) when passing positional arguments through; `$@` unquoted re-splits and merges arguments (shellcheck SC2068).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `"$@"` (quoted) when passing positional arguments through to another command or function.

**Why:** `"$@"` preserves argument boundaries — each positional argument becomes one argument to the called command, even if it contains whitespace or special characters. `$@` unquoted re-splits each argument on `IFS` (typically whitespace) and merges them into a flat string of words, then re-splits on word boundaries. A script invoked as `script.sh "two words" "another arg"` and passing `cmd $@` sends four arguments to `cmd`; passing `cmd "$@"` sends two. Most cases where the developer typed `$@` unquoted are bugs — the script worked because the test arguments happened not to contain spaces.

**How to apply:** always quote `$@` when forwarding arguments: `cmd "$@"`. Same pattern for `"$*"` versus `$*` (though `"$@"` is almost always what you want — `"$*"` joins all args into one string with `IFS[0]` between them, useful for log messages but rarely for command invocation).

```bash
# Before — re-splits args
main() {
  process_file $@
}

# After — preserves arg boundaries
main() {
  process_file "$@"
}
```

```bash
# A function that wraps a command — always "$@"
run_with_logging() {
  printf 'starting: %s\n' "$*" >&2
  "$@"
}

run_with_logging cmd --flag "two words"
```

**Exception:** none in scope. The cases where unquoted `$@` is intentional are in code golf or shell trickery that doesn't belong in a maintained script.
