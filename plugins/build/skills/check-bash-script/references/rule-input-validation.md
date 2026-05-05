---
name: Input Validation and Destructive-Op Safety
description: Validate inputs early before destructive work, gate destructive operations behind dry-run flags, externalize secrets from argv, and use `--` before user-supplied arguments.
paths:
  - "**/*.sh"
  - "**/*.bash"
---

Validate inputs early before any destructive or expensive work, gate destructive operations behind dry-run flags, externalize secrets from argv, and use `--` before user-supplied arguments to commands like `rm`, `grep`, `mv`, and `cp`.

**Why:** "Fail before damage" is cheap to implement and expensive to skip. A destructive operation (delete, overwrite, irreversible network call) that fires before input validation runs against partial or wrong data; the corruption is downstream of where the check could have caught it. `--dry-run` flags that aren't consulted are worse than no flag — they imply a safety mechanism that doesn't exist. Secrets in argv are visible to every other process via `ps`, written to shell history, and may leak through error messages; reading them from environment variables or stdin avoids the leak surface. The `--` separator prevents option-injection from filenames starting with `-` (`rm -- "$path"` treats `$path` as a path, even if it begins with `-rf`).

**How to apply:** at the top of `main`, validate every required input — `${var:?message}` for required positional args; explicit `[[ -e "$path" ]] || die` for paths; explicit `[[ "$value" =~ pattern ]] || die` for format-checked inputs. Wire `--dry-run` (if declared) into every destructive branch. Read secrets from environment, never argv. Add `--` before any user-supplied argument to commands that accept flags.

```bash
main() {
  local input="${1:?usage: script <input-file>}"
  local dry_run="${DRY_RUN:-0}"

  [[ -e "$input" ]] || die "input not found: $input"
  [[ -r "$input" ]] || die "input not readable: $input"

  if [[ "$dry_run" -eq 1 ]]; then
    printf 'would delete: %s\n' "$input"
    return 0
  fi

  rm -f -- "$input"
}
```

**Common fail signals (audit guidance):**
- `rm -rf "$dir"` with no existence check — destroys whatever's at `$dir` if it's wrong, with no second chance.
- `--dry-run` flag declared but never consulted — implies safety that doesn't exist.
- `password=$1` or `secret=$2` — secret in argv, visible to every other process.
- `rm -rf $var` unquoted — word-splitting hazard combined with destructive operation.
- Missing `--` separator in `rm "$path"` — option-injection if `$path` begins with `-`.
- Validation that runs *after* the destructive operation — the check exists but doesn't help.

**Exception:** scripts whose explicit purpose IS to delete without confirmation (e.g., a CI cleanup script with no human in the loop). Document the choice in the header — it's a deliberate inversion, and the dry-run pattern still applies for testing.
