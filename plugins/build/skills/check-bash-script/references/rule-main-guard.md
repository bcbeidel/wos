---
name: Sourceable Guard
description: Gate `main "$@"` behind `[[ "${BASH_SOURCE[0]}" == "${0}" ]]` at the bottom of the file so the script can be sourced for testing without running.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Gate `main "$@"` behind `[[ "${BASH_SOURCE[0]}" == "${0}" ]]` at the bottom of the file so the script can be sourced for testing without triggering `main`.

**Why:** the guard lets the file be sourced for testing — `. ./script.sh` (or `source ./script.sh`) loads helper functions into the current shell without running `main`. Test harnesses like `bats` and `shunit2` rely on this pattern: they source the script under test, then invoke individual functions to assert behavior. Without the guard, `source script.sh` runs the entire script as a side effect, often with the wrong arguments, often with unintended file system effects. The guard is one line and removes a whole class of testing friction.

**How to apply:** place the guard as the last non-comment line of the file. Use `[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"` for terseness, or the explicit `if`-block form for clarity in larger scripts. `BASH_SOURCE[0]` is the path of the file being executed; `$0` is the script-or-shell name. They match when the file is run directly, differ when sourced.

```bash
main() {
  ...
}

# Run main only when executed directly, not when sourced.
[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
```

```bash
# Equivalent explicit form
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
```

**Exception:** scripts that have no `main` (entire file is a function library meant only to be sourced) don't need the guard — there's nothing to gate. Document this in the header ("This file is a function library; source it, do not execute it").
