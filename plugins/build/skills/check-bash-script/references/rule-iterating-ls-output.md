---
name: Iterate with Globs Not ls
description: Iterate filenames with bash globs (`for f in *.ext`), not by parsing `ls` output (shellcheck SC2045).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Iterate filenames with bash globs (`for f in *.ext`); never `for f in $(ls *.ext)`.

**Why:** filenames with spaces, newlines, or leading dashes break `ls`-based iteration. A directory containing `my report.txt` produces two iterations (`my` and `report.txt`) under `for f in $(ls)`; under bash globs (`for f in *.txt`), it produces one iteration with the correct filename. The shell's glob expansion is the right primitive — it handles arbitrary filenames correctly, doesn't require subshelling out to `ls`, and produces an array of matches the script can iterate over without word-splitting hazards.

**How to apply:** replace `for f in $(ls PATTERN)` with `for f in PATTERN`. When no matches exist, the unmatched glob expands to itself by default — guard with `shopt -s nullglob` to make unmatched globs expand to nothing instead. For recursive matches, use `globstar`: `shopt -s globstar; for f in **/*.log; do ...`.

```bash
# Before — breaks on filenames with spaces
for f in $(ls *.log); do
  process "$f"
done

# After — bash glob, safe for arbitrary filenames
for f in *.log; do
  process "$f"
done

# After — guard against no matches
shopt -s nullglob
for f in *.log; do
  process "$f"
done
shopt -u nullglob
```

**Exception:** none in scope. Globs handle every legitimate iteration case more safely than `ls`.

**See also:** `rule-ls-grep-parsing.md` (SC2010), `rule-ls-instead-of-find.md` (SC2012) — sibling rules in the same family. The combined detection signal in shellcheck recognizes any of these three SC codes; each per-rule file documents the specific anti-pattern.
