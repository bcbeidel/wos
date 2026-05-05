---
name: Output Discipline
description: Route data output to stdout, log/error/prompt output to stderr, and ensure every error branch produces a non-zero exit code via a `die` helper.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Route data output to stdout, log and error and prompt output to stderr, and ensure every error branch produces a non-zero exit code — typically via a `die` helper.

**Why:** Unix pipelines depend on the stdout-for-data, stderr-for-chatter convention. A script that prints "processing file X" to stdout silently corrupts every pipeline that consumes its output. Callers in cron, CI, and Makefiles depend on the exit-code contract — an error branch that logs a problem then exits 0 makes the failure invisible to the caller; cron sends no email, CI marks the job green, the bug ships to production. The `die` helper centralizes the "log to stderr + exit non-zero" pattern so every error path follows the same discipline; without it, error paths drift (some `echo`, some `>&2`, some `exit 1`, some `exit 0`) and the contract degrades.

**How to apply:** define a `die` helper for failure paths instead of bare `exit 1` calls without messages. Route error and log output via `>&2` redirection (or through `die`). Ensure every error branch ends with `die` or `exit N` where `N > 0`. Reserve stdout for the script's actual data output — when the script's purpose is to produce a value (a path, a number, a JSON document), that value goes to stdout untouched by progress messages.

```bash
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

main() {
  local input="${1:?usage: script <input>}"
  [[ -e "$input" ]] || die "input not found: $input"
  printf 'processing: %s\n' "$input" >&2   # log to stderr
  produce_data "$input"                     # data to stdout
}
```

**Common fail signals (audit guidance):**
- `echo "error: $err"` without `>&2` — error mixed into stdout, corrupts callers.
- Error branch that logs and then `exit 0` — failure invisible to caller.
- `exit 1` with no preceding message — caller can't diagnose without re-running with strace.
- Bare progress prints on stdout when the script's purpose is to produce data — output stream contaminated.

**Exception:** scripts whose sole purpose IS to produce log output (e.g., a wrapper that runs a command and reformats its output for human reading) can route everything to stdout. Document this in the header — it's a deliberate inversion, not the default.
