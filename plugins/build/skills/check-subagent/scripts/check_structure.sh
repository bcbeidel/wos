#!/usr/bin/env bash
#
# check_structure.sh — Deterministic Tier-1 body-structure check for
# subagent definitions. Emits a JSON ARRAY of two envelopes
# (rule_id="no-headings", "scope-absent") per scripts/_common.py.
#
# Checks:
#   no-headings    body has no ## heading (WARN)
#   scope-absent   no heading matching Scope / In scope / Out of scope
#                  (WARN; was INFO)
#
# Usage:
#   check_structure.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (WARN ok)
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, basename, find, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk basename find python3)

readonly RECIPE_NO_HEADINGS='Add section headings to the body. Minimum: `## Scope`, `## Process` (or `## Workflow`), `## Output`, `## Failure behavior`. Pattern-match peer subagents in the directory. Consistent structure shortens review time and aids mid-task retrieval when the agent re-reads its own prompt.'

readonly RECIPE_SCOPE_ABSENT='Add a `## Scope` section naming what the agent handles and what it refuses. Out-of-scope is as load-bearing as in-scope — it tells the agent when to stop rather than improvise. FROM body describing only what the agent does; TO `## Scope\n\nIn scope: TypeScript files (.ts, .tsx) currently staged.\nOut of scope: untracked files, test files, generated code.`.'

usage() {
  cat <<'EOF'
check_structure.sh — Audit body heading structure.

Usage:
  check_structure.sh <path> [<path> ...]

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings
  1   one or more FAIL findings
  64  usage error
  69  missing dependency
EOF
}

install_hint() {
  case "${1}" in
    awk | basename | find) printf 'should be preinstalled on any POSIX system' ;;
    python3) printf 'install Python 3.9+' ;;
    *) printf 'see your package manager' ;;
  esac
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
      printf '%s: missing required command %q. Install: %s\n' \
        "${PROGNAME}" "${cmd}" "$(install_hint "${cmd}")" >&2
    done
    exit 69
  fi
}

body_headings() {
  awk '
    /^---[[:space:]]*$/ {
      if (++fm_count == 1 && NR == 1) { in_fm = 1; next }
      if (in_fm && fm_count == 2)      { in_fm = 0; next }
    }
    in_fm { next }
    /^##[[:space:]]/ { print }
  ' "$1"
}

# TSV: <rule_id>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  case "${file}" in
    *.md) ;;
    *) return ;;
  esac

  local headings
  headings="$(body_headings "${file}")"

  if [[ -z "${headings}" ]]; then
    printf 'no-headings\t%s\t1\tbody has no ## headings\n' "${file}"
    return
  fi

  if ! printf '%s\n' "${headings}" | awk '
    /^##[[:space:]]+(Scope|In scope|Out of scope)/ { found = 1 }
    /^##[[:space:]]+Scope[[:space:]]*&[[:space:]]*Constraints/ { found = 1 }
    END { exit (found ? 0 : 1) }
  '; then
    printf 'scope-absent\t%s\t1\tno Scope / In scope / Out of scope section\n' \
      "${file}"
  fi
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    emit_raw "${target}"
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      emit_raw "${file}"
    done < <(find "${target}" -maxdepth 1 -type f -name '*.md' 2>/dev/null)
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_SUBAGENT_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipes = {
    "no-headings": os.environ["CHECK_SUBAGENT_RECIPE_NO_HEADINGS"],
    "scope-absent": os.environ["CHECK_SUBAGENT_RECIPE_SCOPE_ABSENT"],
}
order = ["no-headings", "scope-absent"]

per_rule = {r: [] for r in order}
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 3)
    if len(parts) != 4:
        continue
    rule_id, path, lineno, context = parts
    if rule_id not in per_rule:
        continue
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    per_rule[rule_id].append(
        emit_json_finding(
            rule_id=rule_id,
            status="warn",
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=f"{path}: {context}.",
            recommended_changes=recipes[rule_id],
        )
    )

envelopes = [emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in order]
print_envelope(envelopes)
if any(e["overall_status"] == "fail" for e in envelopes):
    sys.exit(1)
'

emit_envelopes() {
  CHECK_SUBAGENT_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SUBAGENT_RECIPE_NO_HEADINGS="${RECIPE_NO_HEADINGS}" \
    CHECK_SUBAGENT_RECIPE_SCOPE_ABSENT="${RECIPE_SCOPE_ABSENT}" \
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
  local target rc=0
  {
    for target in "$@"; do
      scan_path "${target}"
    done
  } | emit_envelopes || rc=$?
  exit "${rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
