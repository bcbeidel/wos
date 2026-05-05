---
name: Variable Expansion Braces
description: Brace variable expansions (`${var}`) when adjacent to identifier characters; `$varfoo` references a different (probably empty) variable.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Brace variable expansions when adjacent to identifier characters: `${var}foo` not `$varfoo`.

**Why:** `"$prefixfoo"` references a variable named `prefixfoo` (probably unset, expanding to empty under strict mode), not the variable `prefix` followed by the literal `foo`. The shell's variable-name parser greedily consumes identifier characters (letters, digits, underscores) following `$`. The braces draw the boundary explicitly: `"${prefix}foo"` means "expand `prefix`, then literal `foo`". Without braces, the bug is silent — strict mode catches the unset variable, but if `prefixfoo` happens to be set elsewhere, the script silently uses the wrong value.

**How to apply:** add braces whenever the expansion is followed by characters that could be part of an identifier (letters, digits, underscores). Other adjacent characters (spaces, slashes, dashes, dots, single quotes) don't require braces but adding them anyway is harmless and consistent. Some teams add braces uniformly to all expansions; the audit only flags the actually-ambiguous cases.

```bash
# Before — ambiguous; "$prefixfoo" looks for variable "prefixfoo"
printf '%s\n' "$prefix$timestamp"
log_path="$dir$name_log"

# After — unambiguous
printf '%s\n' "${prefix}${timestamp}"
log_path="${dir}${name}_log"
```

**Exception:** expansions followed by non-identifier characters (slashes, dots, dashes, brackets) don't need braces because the shell knows the variable name ends. `"$dir/file.txt"` is unambiguous; `"$ext.bak"` is unambiguous. The audit flags only adjacent identifier characters.
