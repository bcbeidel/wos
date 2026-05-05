---
name: Printf Over Echo
description: Use `printf` for non-trivial output (escapes, format specifiers, multi-arg) instead of `echo`; echo's behavior varies across shells and bash builds.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `printf` for non-trivial output — anywhere escapes, format specifiers, or multi-argument output are involved.

**Why:** `echo`'s handling of `-e`, `-n`, and escape sequences varies across shells and even across bash builds (the `xpg_echo` shopt changes interpretation; some macOS bash builds default differently than Linux ones). A script that prints `echo -e "a\tb"` produces `-e a   b` on some systems and `a\tb` on others. `printf` is portable and does what you wrote — the format string is unambiguous, the arguments are explicit. Reserve `echo` for trivial single-argument cases where escape handling doesn't matter.

**How to apply:** replace `echo` with `printf` whenever the output uses escape sequences, the `-e` / `-n` / `-E` flags, or multiple arguments that need spacing. The format string ends with explicit `\n` for trailing newlines (printf doesn't add one).

```bash
# Before — escape-sequence dependent on echo's flags
echo -e "name:\t$name\nvalue:\t$value"

# After — explicit, portable
printf 'name:\t%s\nvalue:\t%s\n' "$name" "$value"
```

```bash
# Before — multi-arg with implicit spacing
echo "hello" "$user" "from" "$host"

# After — explicit format
printf '%s %s %s %s\n' "hello" "$user" "from" "$host"
```

**Exception:** simple single-argument output without escapes is fine with `echo` — `echo "starting build"` is unambiguous and reads cleanly. The audit flags non-trivial cases (escapes, `-e`/`-n`, multi-arg), not every `echo`.
