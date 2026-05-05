---
name: Quote Command Substitutions
description: 'Quote command substitutions: `"$(cmd)"` not `$(cmd)`. Same word-splitting and globbing hazards as unquoted variables (shellcheck SC2046).'
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Quote command substitutions: `"$(cmd)"` not `$(cmd)`.

**Why:** the output of `$(cmd)` is subject to the same word-splitting and globbing as a variable expansion. If `cmd` outputs a path containing spaces, an unquoted `$(cmd)` splits it into multiple arguments; if it outputs `*`, the glob expands to every file in the current directory. The bug surfaces when `cmd`'s output crosses a boundary the developer didn't expect — `$(get_user_dir)` works in test environments where home directories are simple, breaks the moment a user has a space in their home path. See `rule-unquoted-variable-expansion.md` for the parent pattern; this is the same fix applied to substitution output.

**How to apply:** wrap every `$(...)` expansion in double quotes when the output is used as an argument or value: `"$(cmd)"`. For assignments where the output is captured into a variable, the quotes are also recommended for consistency: `result="$(cmd)"`.

```bash
# Before — output of pwd splits/globs
cd $(pwd)/subdir

# After — output preserved as single string
cd "$(pwd)/subdir"
```

```bash
# Before — passes split output as multiple args
process_file $(find_input_path)

# After — passes one path
process_file "$(find_input_path)"
```

**Exception:** when you specifically want command substitution to produce multiple arguments (e.g., reading a file of paths into a `for` loop). Those cases are rare; use `mapfile -t` or `read -ra` instead — they handle quoting correctly without relying on word-splitting.
