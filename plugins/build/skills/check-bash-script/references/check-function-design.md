---
name: Function Design
description: Make `main` an orchestrator of named helpers; keep helpers small and intent-named; provide a sourceable guard at the bottom of the file.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

**Why:** short named helpers read as their own commentary. A `main` that calls `fetch`, `transform`, `validate`, `write` tells a reader the script's flow at a glance; a 200-line `main` that inlines each phase forces the reader to parse implementation to recover intent. The cost of extracting a helper is one function definition and one call site — small. The benefit is durable: future changes happen in named scopes, tests can target individual helpers, and a sourceable guard at the bottom (`[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"`) lets `bats`/`shunit2` load the file without running `main`. The pattern composes with `rule-main-fn.md` and `rule-main-guard.md` — those Tier-1 rules ensure the structure exists; this Tier-2 rule judges whether it's used well.

**How to apply:** when `main` exceeds ~30 lines or contains ≥3 distinct logical phases, extract phases into named helpers. Helper names should be verb phrases (`fetch_data`, `validate_records`, `write_output`), not abstract nouns (`processor`, `handler`). Keep each helper short — under ~30 lines — and single-purpose. The sourceable guard goes at the very bottom.

```bash
main() {
  local input="${1:?usage: script <input>}"
  local raw transformed validated

  raw="$(fetch_data "$input")"
  transformed="$(transform_records "$raw")"
  validate_records "$transformed"
  write_output "$transformed"
}

fetch_data() {
  local source="$1"
  curl -sSf "$source" || die "fetch failed: $source"
}

transform_records() {
  local raw="$1"
  jq '.records[]' <<< "$raw"
}

validate_records() {
  local records="$1"
  [[ -n "$records" ]] || die "no records to validate"
  # ... validation logic
}

write_output() {
  local records="$1"
  printf '%s\n' "$records"
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"
```

**Common fail signals (audit guidance):**
- A 200-line `main` that inlines fetch + transform + validate + write — extract phases.
- Helper names like `do_stuff`, `process`, `handler` — names that don't tell the reader what they do.
- The file is not sourceable — no guard, or the guard is missing/wrong.
- Helpers that share state via global variables instead of arguments — fragile coupling.
- One helper doing two things (fetching + validating) — split into two.

**Exception:** short scripts where the entire logic fits in `main` cleanly (under ~30 lines, single responsibility). Premature extraction adds ceremony for no benefit; the audit calls out the cases where extraction would clearly help.
