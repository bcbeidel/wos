---
name: Avoid Useless Cat
description: Pipe directly from a file rather than `cat file | cmd` — one extra fork for no benefit (shellcheck SC2002).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Pipe directly from a file rather than `cat file | cmd`.

**Why:** shellcheck flags `cat file | cmd` as a useless use of `cat` — one extra process and pipe for no benefit. `cmd file` (when supported) or `< file cmd` (the redirect form) does the same thing without the extra fork. The cost is microscopic per invocation but adds up in tight loops, and the pattern is a well-known stylistic flag in code review. Some authors prefer the left-to-right `cat file | cmd` reading order — when that's the case, leaving the pattern in with a `# shellcheck disable=SC2002` justification is acceptable.

**How to apply:** replace `cat file | cmd` with `cmd file` when the command accepts a file argument; otherwise use the redirect form `< file cmd`. The redirect form preserves left-to-right reading: `< input.txt grep pattern`.

```bash
# Before — extra fork
cat file | grep pattern

# After — cmd takes a file arg
grep pattern file

# After — redirect form (preserves reading order)
< file grep pattern
```

**Exception:** when the left-to-right reading order is genuinely important to the script's clarity (rare, but real for long pipelines that start with a file and process it through many stages). Use `# shellcheck disable=SC2002` on the line, with a brief comment explaining the choice.
