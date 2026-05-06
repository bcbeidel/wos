#!/usr/bin/env bash
#
# check_size.sh — Deterministic Tier-1 body-size check for subagent
# definitions. Emits a JSON ARRAY containing a single envelope
# (rule_id="size") per scripts/_common.py.
#
# Measures the character count of the markdown body (everything after
# the frontmatter block). Soft WARN at >=6,000 chars (~1,500 tokens);
# hard FAIL at >=12,000 chars (~3,000 tokens). Single rule with
# conditional severity. Thresholds derived from the ensemble synthesis.
#
# Usage:
#   check_size.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, basename, find, wc, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly SOFT_THRESHOLD=6000
readonly HARD_THRESHOLD=12000

readonly REQUIRED_CMDS=(awk basename find wc python3)

readonly RECIPE_SIZE='Trim the body. Target <=1,500 tokens (~6,000 chars). Move reference material into linked files; collapse redundant examples; remove expansions. At >=12,000 chars (~3,000 tokens) split the workflow — a subagent that needs this much prompt is probably two agents, or carrying documentation that belongs in a shared reference. The prompt competes directly with task context at this size.'

usage() {
  cat <<'EOF'
check_size.sh — Flag subagent definitions with oversized prompt bodies.

Usage:
  check_size.sh <path> [<path> ...]

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings (WARN ok)
  1   one or more FAIL findings
  64  usage error
  69  missing dependency
EOF
}

install_hint() {
  case "${1}" in
    awk | basename | find | wc) printf 'should be preinstalled on any POSIX system' ;;
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

body_text() {
  awk '
    BEGIN { in_body = 0; fm_count = 0 }
    in_body { print; next }
    /^---[[:space:]]*$/ {
      fm_count++
      if (NR == 1 && fm_count == 1) { in_fm = 1; next }
      if (in_fm && fm_count == 2)   { in_fm = 0; in_body = 1; next }
    }
    !in_fm && NR == 1 {
      in_body = 1
      print
    }
    in_fm { next }
  ' "$1"
}

# TSV: <status>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  case "${file}" in
    *.md) ;;
    *) return ;;
  esac

  local body_chars
  body_chars="$(body_text "${file}" | wc -c | awk '{print $1}')"

  if [[ "${body_chars}" -ge "${HARD_THRESHOLD}" ]]; then
    printf 'fail\t%s\t1\tbody is %s chars (>=%s, ~3,000 tokens)\n' \
      "${file}" "${body_chars}" "${HARD_THRESHOLD}"
  elif [[ "${body_chars}" -ge "${SOFT_THRESHOLD}" ]]; then
    printf 'warn\t%s\t1\tbody is %s chars (>=%s, ~1,500 tokens)\n' \
      "${file}" "${body_chars}" "${SOFT_THRESHOLD}"
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

recipe = os.environ["CHECK_SUBAGENT_RECIPE_SIZE"]

findings = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 3)
    if len(parts) != 4:
        continue
    status, path, lineno, context = parts
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    findings.append(
        emit_json_finding(
            rule_id="size",
            status=status,
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=f"{path}: {context}.",
            recommended_changes=recipe,
        )
    )

envelope = emit_rule_envelope(rule_id="size", findings=findings)
print_envelope([envelope])
if envelope["overall_status"] == "fail":
    sys.exit(1)
'

emit_envelopes() {
  CHECK_SUBAGENT_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SUBAGENT_RECIPE_SIZE="${RECIPE_SIZE}" \
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
