---
name: Quote Variable Expansions
description: Quote variable expansions to prevent word-splitting and globbing — the single largest source of real-world bash bugs (shellcheck SC2086).
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Quote variable expansions: `"$var"` not `$var`. Quote array element expansions: `"${arr[@]}"` not `${arr[@]}`.

**Why:** without quotes, `$var` undergoes word-splitting on `IFS` (which a previous part of the script may have changed) and pathname expansion (globbing on `*`, `?`, `[...]`). A filename containing a space becomes two arguments; a value containing `*` glob-expands to every matching path in the current directory. This is the single largest source of real-world bash bugs — accidentally invoking a destructive command on every file in `pwd`, accidentally splitting a multi-word configuration value into nonsense — and it shows up in production scripts that worked fine on the developer's no-spaces test data and broke on the customer's filename-with-spaces.

**How to apply:** quote every variable expansion with double quotes. For arrays, expand with `"${arr[@]}"` (each element becomes one argument). For substring expansions and glob-relative tests where you want word-splitting, the quotes can come off — but those cases are rare and worth a comment.

```bash
# Before — splits and globs $files
for f in $files; do
  process "$f"
done

# After — single string, no splitting
for f in "$files"; do
  process "$f"
done

# After — array, one argument per element
for f in "${files[@]}"; do
  process "$f"
done
```

```bash
# Function arguments — always quote
do_work "$user_input" "$path"
```

**Exception:** none worth defending. The handful of cases where you genuinely want word-splitting (parsing a known-safe space-delimited string) are vanishingly rare; when they arise, comment the choice and the audit will accept the documented exception.
