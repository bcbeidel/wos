---
name: Naming
description: Use `snake_case` for local variables, `UPPERCASE` for env vars and module-level constants, intent-naming throughout, and avoid shadowing builtins.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Use `snake_case` for local variables and function names, `UPPERCASE` for exported env vars and module-level `readonly` constants, descriptive intent-naming throughout, and avoid shadowing shell builtins.

**Why:** bash's lack of static types makes naming the load-bearing documentation. A reader scanning the script learns variables' roles only from their names; `Tmp` and `x` and `do_thing` force re-derivation from the body, while `raw_records` and `row_count` and `fetch_log_dir` make intent obvious. The case convention (`snake_case` for locals, `UPPERCASE` for exports/constants) signals scope at a glance — when the reader sees `LOG_DIR`, they know it's a configuration constant; when they see `tmpdir`, they know it's a local variable. Shadowing builtins (`local set=...`, `local echo=...`, `local local=...`) doesn't error but produces confusing scripts where reading "echo" no longer means what it usually does.

**How to apply:** local variables and function names use `snake_case` (`row_count`, `fetch_data`). Module-level `readonly` constants and exported env vars use `UPPERCASE` (`TIMEOUT`, `LOG_DIR`, `OPENAI_API_KEY`). Names state intent — what the value represents, not what it is mechanically. Avoid single-letter names except in short loops (`for i in 1..3`). Avoid names that shadow shell builtins (`local`, `set`, `echo`, `printf`, `read`, `unset`).

```bash
# Before
some_function() {
  local Tmp=$(get_data)
  local x=$(count "$Tmp")
  local data="$Tmp"
}

# After
some_function() {
  local raw_records
  raw_records="$(get_data)"

  local row_count
  row_count="$(count "$raw_records")"
}
```

```bash
# Before — shadows the shell builtin
local echo="hello"

# After — different name
local greeting="hello"
```

**Common fail signals (audit guidance):**
- `local Tmp=...` (capitalized local) or `local x=...` (single-letter at module scope) — case violation.
- Function named `do_stuff`, `do_thing`, `process_it`, `handler` — intent isn't named.
- Local variable named `local`, `set`, `echo`, `printf`, `read`, `unset`, or other builtin — shadowing.
- Module constants in lowercase (`timeout=30` at top level) — case violation; should be `TIMEOUT=30` with `readonly`.
- Loop counters with single letters in long loops — fine in `for i in 1..3`, problematic in 50-iteration loops where `i` could be `entry` or `record`.

**Exception:** loop iterators in short, contained loops can use single-letter names (`for i in 1..3`, `for c in {a..z}`). The audit's judgment surfaces consistent violations across the script, not isolated short-loop counters.
