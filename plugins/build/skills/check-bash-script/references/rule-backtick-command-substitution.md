---
name: Modern Command Substitution
description: Use `$(cmd)` for command substitution, not backticks. `$(...)` is nestable, more readable, and universally supported (shellcheck SC2006).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `$(cmd)` for command substitution; avoid backticks.

**Why:** `$(...)` is nestable (`$(cmd1 $(cmd2))` works; backticks require awkward escaping), more readable (the boundaries are visually obvious; backticks blur with single quotes in many fonts), and universally supported by linters and modern shells. Backticks are a 1980s relic — they predate POSIX and remained for backward compatibility with very old `sh`. There is no reason to use them in a bash-only script: the syntax is harder to read, harder to nest, and shellcheck flags it on every occurrence.

**How to apply:** replace every `` `cmd` `` with `$(cmd)`. The change is mechanical and safe — `$(...)` is strictly more capable than backticks. Combine with quoting (see `rule-unquoted-command-substitution.md`) to get `"$(cmd)"`.

```bash
# Before
count=`wc -l < file`
result=`grep pattern \`find . -name '*.txt'\``

# After
count="$(wc -l < file)"
result="$(grep pattern "$(find . -name '*.txt')")"
```

**Exception:** none. The audit fires on every backtick substitution; the fix is mechanical.
