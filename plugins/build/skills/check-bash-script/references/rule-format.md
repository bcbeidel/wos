---
name: shfmt Canonical Format
description: Format bash scripts with `shfmt -i 2 -ci -bn` so the canonical layout (2-space indent, case-indent, binop on next line) is the source of truth.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Format bash scripts with `shfmt -i 2 -ci -bn` so the canonical layout — 2-space indent, case statement indented, binary operators on the next line — is the source of truth.

**Why:** formatter drift produces noisy diffs and triggers the "someone fix the spacing" PR trickle that no one wants to be the person to write. Letting a tool own the format eliminates the bikeshedding (the team adopts one set of flags and stops debating) and prevents drift (every script is reformatted the same way, regardless of who edited it last). `shfmt` is the de facto standard for bash; it's mechanical, fast, and handles the cases bash humans get wrong (heredoc indentation, complex `case` patterns, line continuations).

**How to apply:** run `shfmt -w -i 2 -ci -bn <file>` to apply the canonical format in place. The flags: `-i 2` is 2-space indent (matches Google Shell Style Guide), `-ci` indents `case` patterns, `-bn` puts binary operators on the next line for readability. A pre-commit hook running `shfmt -d` (diff mode) catches drift in CI.

```bash
# Apply formatting
shfmt -w -i 2 -ci -bn script.sh

# Check formatting (CI)
shfmt -d -i 2 -ci -bn script.sh
```

**Exception:** none in scope. The fix is mechanical; running the formatter takes one command and produces the canonical output. If a team prefers different flags, change them in the SKILL convention, not per-file.
