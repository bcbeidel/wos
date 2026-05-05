---
name: Line Length Cap
description: Keep bash lines under 100 characters; long lines are unreadable in code review and break side-by-side diff views.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Keep bash lines under 100 characters.

**Why:** long lines are unreadable in code review and break side-by-side diff views. The 100-character threshold matches the Google Shell Style Guide convention and is wide enough to accommodate typical bash idioms (variable expansions with quoting, command substitutions with arguments) without forcing artificial breaks. Past 100 characters, lines either wrap in editors (jumbled visual reading) or scroll horizontally (lost context); in `git diff` side-by-side, long lines cut off mid-clause. The fix is mechanical: bash supports line continuation (`\`) and multi-line subshells, both of which break long lines into readable chunks.

**How to apply:** break long lines with `\` continuations (preserving shell semantics: a `\` at end of line continues to the next), or extract complex pipelines into helper functions named for what they do. Multi-line subshells (`$(\n...\n)`) work cleanly for command substitutions with multiple flags.

```bash
# Before — 130+ characters
result="$(some_command --with --many --flags --and "$arg" --more "$another" 2>/dev/null || die "failed")"

# After — line continuation
result="$(some_command --with --many --flags --and "$arg" --more "$another" 2>/dev/null \
  || die "some_command failed")"

# After — multi-line subshell
result="$(
  some_command --with --many --flags \
    --and "$arg" --more "$another" 2>/dev/null \
    || die "some_command failed"
)"
```

**Exception:** lines containing a single long string literal (a URL, a regex, a heredoc-equivalent) where breaking would obscure meaning. The audit emits WARN (judgment-level), not FAIL — leave a comment if breaking would harm readability and the reader can disagree.
