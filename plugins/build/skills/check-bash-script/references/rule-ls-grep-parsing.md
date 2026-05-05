---
name: Avoid ls | grep
description: Use globs or `find` to filter filenames; `ls | grep` parses unstable output and breaks on filenames with spaces or special characters (shellcheck SC2010).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use globs or `find` to filter filenames; avoid `ls | grep`.

**Why:** `ls | grep` parses output that isn't designed for parsing — `ls` formats for humans, with column alignment that varies, locale-dependent metadata, and filenames that may contain whitespace, newlines, or characters that confuse `grep`. A filename with a leading dash is interpreted as a flag; a filename with embedded newlines fragments across lines and matches the wrong `grep` patterns. The fix uses bash globs (which the shell expands using actual filesystem traversal) or `find` (which produces null-delimitable, machine-parseable output).

**How to apply:** replace `ls | grep PATTERN` with a bash glob (`*.log`, `**/*.log`) or with `find . -name 'PATTERN'`. For the iteration case, see `rule-iterating-ls-output.md`. For the parsing case where you wanted file metadata, see `rule-ls-instead-of-find.md`.

```bash
# Before — fragile
files=$(ls | grep '\.log$')

# After — bash glob
files=( *.log )

# After — find for recursive cases
files=( $(find . -name '*.log' -print0 | xargs -0 echo) )
```

**Exception:** none in scope. Every `ls | grep` has a clean replacement; the audit's job is to surface the pattern so the replacement happens.

**See also:** `rule-ls-instead-of-find.md` (SC2012) and `rule-iterating-ls-output.md` (SC2045) — the same family of `ls`-parsing anti-patterns, each with its own specific shape.
