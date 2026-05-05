---
name: Double-Bracket Test
description: Use `[[ ... ]]` for test expressions in bash scripts; `[ ... ]` is the POSIX form and brings word-splitting hazards bash doesn't need.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `[[ ... ]]` for test expressions in bash scripts.

**Why:** `[[ ]]` doesn't word-split inside the brackets, so unquoted variables behave predictably; supports pattern matching with `==` and `=~`; has saner numeric and string comparison operators (`<`, `>`, `<=`, `>=`); and short-circuits `&&` / `||` correctly. The POSIX `[ ]` form keeps existing in bash for portability with `dash` and `busybox sh`, but this skill is bash-only — there's no portability cost in switching, and several real-world classes of bug (unquoted `$x` word-splitting inside `[ ]`) disappear.

**How to apply:** replace `[ ... ]` with `[[ ... ]]` in test expressions. Use `==` instead of `=` for clarity (both work in `[[ ]]`). Keep `[[ ]]` consistently — mixing the two forms in one script invites confusion about which rules apply where.

```bash
# Before
if [ "$x" = "y" ]; then
  ...
fi

# After
if [[ "$x" == "y" ]]; then
  ...
fi

# Pattern matching (only available in [[ ]])
if [[ "$file" == *.log ]]; then
  ...
fi

# Regex (only available in [[ ]])
if [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  ...
fi
```

**Exception:** none in scope. Files routed to this skill are bash; bash supports `[[ ]]`. Files needing POSIX-shell portability route to a different primitive before authoring.
