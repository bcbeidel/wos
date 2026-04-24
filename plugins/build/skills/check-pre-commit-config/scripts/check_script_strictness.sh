#!/usr/bin/env bash
#
# check_script_strictness.sh — Tier-1 deterministic check for local
# pre-commit hook shell scripts.
#
# For every path argument, asserts:
#   - First line is a bash shebang (#!/usr/bin/env bash or #!/bin/bash)
#   - `set -euo pipefail` (or equivalent) appears in the first 20
#     non-comment lines
#
# Usage:
#   check_script_strictness.sh <script.sh> [<script.sh> ...]
#
# Dependencies: grep, head, awk
#
# Exit codes:
#   0   clean / INFO only
#   1   one or more FAIL findings
#   64  usage error
#   69  missing required dependency

set -euo pipefail
IFS=$'\n\t'

readonly PROGNAME="$(basename "${0}")"

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

emit() {
  local severity="$1"
  local path="$2"
  local check="$3"
  local detail="$4"
  local recommendation="$5"
  printf '%s  %s — %s: %s\n' "$severity" "$path" "$check" "$detail"
  printf '  Recommendation: %s\n' "$recommendation"
}

preflight() {
  local cmd
  for cmd in grep head awk; do
    command -v "$cmd" >/dev/null 2>&1 || {
      printf 'error: missing required command: %s\n' "$cmd" >&2
      exit 69
    }
  done
}

check_file() {
  local path="$1"
  local fails=0

  if [[ ! -r "$path" ]]; then
    emit "FAIL" "$path" "shell-strictness" \
      "cannot read file" \
      "Verify the path referenced by the hook exists and is readable."
    return 1
  fi

  local first_line
  first_line="$(head -n 1 "$path")"

  if [[ ! "$first_line" =~ ^\#\!.*(bash|env\ bash)([[:space:]]|$) ]]; then
    emit "FAIL" "$path" "shell-strictness" \
      "first line is not a bash shebang" \
      "Add '#!/usr/bin/env bash' as the first line."
    fails=$((fails + 1))
  fi

  # Look for strict-mode directive in the first 20 non-blank, non-comment lines.
  # Accepts: `set -euo pipefail`, `set -Eeuo pipefail`, `set -eou pipefail`,
  # or `set -e` / `set -u` / `set -o pipefail` spread across multiple lines.
  local prologue
  prologue="$(head -n 50 "$path" | awk 'NF && !/^[[:space:]]*#/' | head -n 20)"

  local has_errexit has_nounset has_pipefail
  has_errexit="$(printf '%s\n' "$prologue" | grep -cE '^[[:space:]]*set[[:space:]]+-[^[:space:]]*e' || true)"
  has_nounset="$(printf '%s\n' "$prologue" | grep -cE '^[[:space:]]*set[[:space:]]+-[^[:space:]]*u' || true)"
  has_pipefail="$(printf '%s\n' "$prologue" | grep -cE '(^|[[:space:]])pipefail([[:space:]]|$)' || true)"

  if [[ "$has_errexit" -eq 0 || "$has_nounset" -eq 0 || "$has_pipefail" -eq 0 ]]; then
    emit "FAIL" "$path" "shell-strictness" \
      "'set -euo pipefail' not found in first 20 non-comment lines" \
      "Add 'set -euo pipefail' (and a safe IFS) near the top of the script."
    fails=$((fails + 1))
  fi

  return "$fails"
}

main() {
  if [[ "$#" -eq 0 ]]; then
    printf 'usage: %s <script.sh> [<script.sh> ...]\n' "$PROGNAME" >&2
    exit 64
  fi

  preflight

  local total_fails=0
  local path
  for path in "$@"; do
    local file_fails=0
    check_file "$path" || file_fails="$?"
    total_fails=$((total_fails + file_fails))
  done

  [[ "$total_fails" -eq 0 ]] || exit 1
  exit 0
}

# Sourceable guard: run main only when executed, not when sourced.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
