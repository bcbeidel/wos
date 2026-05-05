---
name: Use Find Instead of ls -l
description: Use `find` for programmatic file metadata; `ls -l` output format is unstable and breaks on locale differences (shellcheck SC2012).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `find` (or `stat`) for programmatic file metadata; avoid parsing `ls -l` output.

**Why:** `ls -l`'s output format is not stable across implementations or locales — column widths shift, date formats vary by `LANG`, file-mode strings differ between BusyBox and GNU. Scripts that parse `ls -l` to extract size, owner, or modification time work in development and break in production when an environment variable changes the locale. `find -printf` (or `stat -c`/`stat -f` per platform) emits explicit, parseable formats — the script names the fields it wants and gets them in a known order.

**How to apply:** replace `ls -l` parsing with `find` using `-printf` for explicit field extraction, or `stat` for single-file metadata. When the script wants to act on filenames (move, copy, process), `find` plus `-print0`/`xargs -0` handles arbitrary filenames safely.

```bash
# Before — parses unstable ls -l output
size=$(ls -l "$file" | awk '{print $5}')

# After — stat with explicit format
size=$(stat -c '%s' "$file" 2>/dev/null || stat -f '%z' "$file")

# After — find with -printf
find . -maxdepth 1 -type f -printf '%s %p\n'
```

**Exception:** human-facing output where the script is just calling `ls -l` to display files to the user — no parsing. The audit flags `ls -l | <pipeline>` patterns, not interactive display.

**See also:** `rule-ls-grep-parsing.md` (SC2010) and `rule-iterating-ls-output.md` (SC2045) — sibling rules in the `ls`-parsing anti-pattern family.
