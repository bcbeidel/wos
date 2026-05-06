#!/usr/bin/env bash
#
# check_actionlint.sh — Tier-1 wrapper for `actionlint`, the canonical
# GitHub Actions workflow schema / expression / shellcheck-integrated
# linter. Emits a JSON ARRAY with a single envelope (rule_id="actionlint",
# WARN) per scripts/_common.py.
#
# actionlint is optional — when absent, this script emits a single
# inapplicable envelope and exits 0.
#
# Usage:
#   check_actionlint.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (including when actionlint is absent)
#   1   one or more FAIL findings (not produced — output is WARN)
#   64  usage error
#   69  missing required dependency

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(find sort python3)

readonly RECIPE_ACTIONLINT='Apply the actionlint suggestion. Actionlint findings are schema, expression, and shell issues with specific, prescriptive fixes — follow the tool description verbatim. Actionlint is the most comprehensive workflow schema validator; its rule-level output is the source of truth. See https://github.com/rhysd/actionlint/blob/main/docs/checks.md for rule details.'

usage() {
  cat <<EOF
check_actionlint.sh — actionlint wrapper for GitHub Actions workflows.

Usage:
  check_actionlint.sh <path> [<path> ...]

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings (or actionlint absent)
  1   one or more FAIL findings (not produced)
  64  usage error
  69  missing dependency
EOF
}

preflight() {
  local missing=()
  local cmd
  for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
      missing+=("${cmd}")
    fi
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    for cmd in "${missing[@]}"; do
      printf '%s: missing required command %q\n' "${PROGNAME}" "${cmd}" >&2
    done
    exit 69
  fi
}

collect_targets() {
  local arg
  for arg in "$@"; do
    if [[ -d "${arg}" ]]; then
      find "${arg}" -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) -print0 | sort -z
    elif [[ -f "${arg}" ]]; then
      printf '%s\0' "${arg}"
    fi
  done
}

readonly EMIT_INAPPLICABLE_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_WF_SCRIPT_DIR"])
from _common import emit_rule_envelope, print_envelope

print_envelope([emit_rule_envelope(rule_id="actionlint", findings=[], inapplicable=True)])
'

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_WF_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipe = os.environ["CHECK_WF_RECIPE_ACTIONLINT"]
findings = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 3)
    if len(parts) != 4:
        continue
    path, lineno_s, _col, message = parts
    try:
        lineno = int(lineno_s)
    except ValueError:
        lineno = 1
    findings.append(
        emit_json_finding(
            rule_id="actionlint",
            status="warn",
            location={"line": lineno, "context": f"{path}:{lineno_s}: {message}"},
            reasoning=f"actionlint at line {lineno} of {path}: {message}.",
            recommended_changes=recipe,
        )
    )

envelope = emit_rule_envelope(rule_id="actionlint", findings=findings)
print_envelope([envelope])
if envelope["overall_status"] == "fail":
    sys.exit(1)
'

emit_inapplicable() {
  CHECK_WF_SCRIPT_DIR="${SCRIPT_DIR}" python3 -c "${EMIT_INAPPLICABLE_PY}"
}

emit_envelopes() {
  CHECK_WF_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_WF_RECIPE_ACTIONLINT="${RECIPE_ACTIONLINT}" \
    python3 -c "${EMIT_PY}"
}

main() {
  if [[ "$#" -eq 0 ]]; then
    usage >&2
    exit 64
  fi
  case "${1:-}" in
    -h | --help)
      usage
      exit 0
      ;;
  esac
  preflight

  if ! command -v actionlint >/dev/null 2>&1; then
    emit_inapplicable
    printf '%s: actionlint not installed — install via `brew install actionlint` (macOS) or `go install github.com/rhysd/actionlint/cmd/actionlint@latest`.\n' \
      "${PROGNAME}" >&2
    exit 0
  fi

  local -a targets=()
  local file
  while IFS= read -r -d '' file; do
    targets+=("${file}")
  done < <(collect_targets "$@")

  if [[ ${#targets[@]} -eq 0 ]]; then
    printf '[]\n'
    exit 0
  fi

  # actionlint output: <path>:<line>:<col>: <message> [<rule>]
  local output
  output="$(actionlint -no-color "${targets[@]}" 2>&1 || true)"

  local rc=0
  {
    if [[ -n "${output}" ]]; then
      while IFS= read -r line; do
        if [[ "${line}" =~ ^([^:]+):([0-9]+):([0-9]+):\ (.+)$ ]]; then
          printf '%s\t%s\t%s\t%s\n' \
            "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" \
            "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}"
        fi
      done <<< "${output}"
    fi
  } | emit_envelopes || rc=$?
  exit "${rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
