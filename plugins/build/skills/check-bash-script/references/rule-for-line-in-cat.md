---
name: Read Lines With While Read
description: Read file lines with `while IFS= read -r line; do ... done < file`; `for line in $(cat file)` word-splits and globs each line (shellcheck SC2013).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Read file lines with `while IFS= read -r line; do ... done < file` — never `for line in $(cat file)`.

**Why:** the `for line in $(cat file)` idiom doesn't read lines; it word-splits the entire file's contents on `IFS` (whitespace by default) and globs each token. A file containing `hello world\nfoo bar` produces four iterations (`hello`, `world`, `foo`, `bar`), not two. Pathnames in the file are also glob-expanded — a line containing `*` becomes every matching path in the current directory. The `while IFS= read -r` form reads one line per iteration, with `IFS=` preventing leading/trailing whitespace stripping and `-r` preventing backslash-escape interpretation.

**How to apply:** replace `for line in $(cat file); do` with `while IFS= read -r line; do ... done < file`. The redirect at the end (`< file`) feeds the file's contents into the loop's stdin. For files where the last line has no trailing newline, add `[[ -n "$line" ]] || break` after the body — the loop variable holds the partial line on the final read.

```bash
# Before — word-splits and globs
for line in $(cat file); do
  process "$line"
done

# After — proper line-by-line read
while IFS= read -r line; do
  process "$line"
done < file

# After — handle missing final newline
while IFS= read -r line || [[ -n "$line" ]]; do
  process "$line"
done < file
```

**Exception:** none in scope. The `while read` pattern handles every legitimate use case correctly.

**See also:** `rule-read-without-r.md` (SC2162) — sibling rule. The combined source recipe addressed both `for line in $(cat)` and `read` without `-r`; this file covers the `for` variant, the sibling covers the `read -r` variant.
