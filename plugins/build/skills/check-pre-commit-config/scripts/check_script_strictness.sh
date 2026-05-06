#!/usr/bin/env bash
#
# check_script_strictness.sh — Tier-1 deterministic check for local
# pre-commit hook shell scripts. Emits JSON envelope per
# scripts/_common.py.
#
# Single-rule script: rule_id="shell-strictness". For every shell
# script path argument, asserts:
#   - First line is a bash shebang (#!/usr/bin/env bash or #!/bin/bash)
#   - `set -euo pipefail` (or equivalent) appears in the first 20
#     non-comment lines
#
# Usage:
#   check_script_strictness.sh <script.sh> [<script.sh> ...]
#
# Dependencies: grep, head, awk, python3
#
# Exit codes:
#   0   overall_status pass / warn / inapplicable
#   1   overall_status=fail
#   64  usage error
#   69  missing required dependency

set -euo pipefail
IFS=$'\n\t'

readonly PROGNAME="$(basename "${0}")"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly RECIPE_SHELL_STRICTNESS='Add `#!/usr/bin/env bash` as the first line and `set -euo pipefail` (with `IFS=$'\''\n\t'\''` for safety) within the first 20 non-comment lines.

Example:
    #!/usr/bin/env bash
    set -euo pipefail
    IFS=$'\''\n\t'\''
    ...

Strict mode turns silent failures, unset-variable typos, and mid-pipeline errors into loud, early exits — required for hook scripts where bypass is automatic on non-zero exit.'

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

preflight() {
  local cmd
  for cmd in grep head awk python3; do
    command -v "$cmd" >/dev/null 2>&1 || {
      printf 'error: missing required command: %s\n' "$cmd" >&2
      exit 69
    }
  done
}

# Emit findings as TSV: <path>\t<message>
emit_raw() {
  local path="$1"

  if [[ ! -r "$path" ]]; then
    printf '%s\tcannot read file\n' "$path"
    return
  fi

  local first_line
  first_line="$(head -n 1 "$path")"

  if [[ ! "$first_line" =~ ^\#\!.*(bash|env\ bash)([[:space:]]|$) ]]; then
    printf '%s\tfirst line is not a bash shebang\n' "$path"
  fi

  # Look for strict-mode directive in first 20 non-blank, non-comment lines.
  local prologue
  prologue="$(head -n 50 "$path" | awk 'NF && !/^[[:space:]]*#/' | head -n 20)"

  local has_errexit has_nounset has_pipefail
  has_errexit="$(printf '%s\n' "$prologue" | grep -cE '^[[:space:]]*set[[:space:]]+-[^[:space:]]*e' || true)"
  has_nounset="$(printf '%s\n' "$prologue" | grep -cE '^[[:space:]]*set[[:space:]]+-[^[:space:]]*u' || true)"
  has_pipefail="$(printf '%s\n' "$prologue" | grep -cE '(^|[[:space:]])pipefail([[:space:]]|$)' || true)"

  if [[ "$has_errexit" -eq 0 || "$has_nounset" -eq 0 || "$has_pipefail" -eq 0 ]]; then
    printf '%s\t%s\n' "$path" "'set -euo pipefail' not found in first 20 non-comment lines"
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_PRECOMMIT_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipe = os.environ["CHECK_PRECOMMIT_RECIPE"]
findings = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line or "\t" not in line:
        continue
    path, message = line.split("\t", 1)
    findings.append(
        emit_json_finding(
            rule_id="shell-strictness",
            status="fail",
            location={"line": 0, "context": path},
            reasoning=f"{path}: {message}.",
            recommended_changes=recipe,
        )
    )
envelope = emit_rule_envelope("shell-strictness", findings)
print_envelope(envelope)
sys.exit(1 if envelope["overall_status"] == "fail" else 0)
'

emit_envelope() {
  CHECK_PRECOMMIT_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_PRECOMMIT_RECIPE="${RECIPE_SHELL_STRICTNESS}" \
    python3 -c "${EMIT_PY}"
}

main() {
  if [[ "$#" -eq 0 ]]; then
    printf 'usage: %s <script.sh> [<script.sh> ...]\n' "$PROGNAME" >&2
    exit 64
  fi

  preflight

  local path
  # Pipefail propagates emit_envelope's exit code (0 or 1) up through
  # set -e to control this script's overall exit code.
  {
    for path in "$@"; do
      emit_raw "$path"
    done
  } | emit_envelope
}

# Sourceable guard.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
