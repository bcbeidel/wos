#!/usr/bin/env bash
#
# check_size.sh — Deterministic Tier-1 size checks for Claude Code
# SKILL.md files. Emits a JSON ARRAY of two envelopes
# (rule_id="body-length", rule_id="line-length") per scripts/_common.py.
#
# Body length:  WARN at ≥300 non-blank lines; FAIL at ≥400 non-blank
#               lines (single rule, conditional severity).
# Line length:  WARN on any line outside fenced code blocks and bare
#               URLs that exceeds 120 chars.
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
#   awk, find, basename, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename python3)
readonly WARN_LINES=300
readonly FAIL_LINES=400
readonly MAX_LINE_LEN=120

readonly RECIPE_BODY_LENGTH='Move reference material, long examples, or complex scripts into sibling files under `references/` and `scripts/`. Treat 300 non-blank lines as the soft cap (WARN) and 400 as the hard ceiling (FAIL). Past 400 lines a skill stops being a skill and becomes a document; the agent reads less of it reliably on each invocation. Every line is paid for in context tokens at invocation time.'

readonly RECIPE_LINE_LENGTH='Wrap the line at a natural clause boundary; in prose, break before a conjunction or after a complete clause. The 120-char cap improves diff readability and matches toolkit-wide conventions. Fenced code blocks and bare-URL-only lines are excluded.'

usage() {
  cat <<EOF
check_size.sh — Size checks for Claude Code SKILL.md files.

Usage:
  check_size.sh <path> [<path> ...]

Checks:
  body-length   WARN at ≥${WARN_LINES} non-blank lines, FAIL at ≥${FAIL_LINES}
  line-length   WARN on any line > ${MAX_LINE_LEN} chars (fenced blocks and
                bare URLs are excluded)

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
    awk | find | basename) printf 'should be preinstalled on any POSIX system' ;;
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

count_non_blank() {
  awk 'NF { n++ } END { print n + 0 }' "$1"
}

# Emit findings as TSV: <rule_id>\t<status>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  local n
  n="$(count_non_blank "${file}")"
  if [[ "${n}" -ge "${FAIL_LINES}" ]]; then
    printf 'body-length\tfail\t%s\t1\t%s non-blank lines (hard ceiling %s)\n' \
      "${file}" "${n}" "${FAIL_LINES}"
  elif [[ "${n}" -ge "${WARN_LINES}" ]]; then
    printf 'body-length\twarn\t%s\t1\t%s non-blank lines (soft cap %s)\n' \
      "${file}" "${n}" "${WARN_LINES}"
  fi

  while IFS=$'\t' read -r lineno length; do
    [[ -z "${lineno}" ]] && continue
    printf 'line-length\twarn\t%s\t%s\tline is %s chars (> %s)\n' \
      "${file}" "${lineno}" "${length}" "${MAX_LINE_LEN}"
  done < <(awk -v max="${MAX_LINE_LEN}" '
    BEGIN { in_fence = 0 }
    {
      if ($0 ~ /^[[:space:]]*```/) { in_fence = !in_fence; next }
      if ($0 ~ /^[[:space:]]*~~~/) { in_fence = !in_fence; next }
      if (in_fence) { next }
      if (NF == 1 && $1 ~ /^https?:\/\//) { next }
      if (length($0) > max) {
        printf "%d\t%d\n", NR, length($0)
      }
    }
  ' "${file}")
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    emit_raw "${target}"
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      emit_raw "${file}"
    done < <(
      find "${target}" -type f -name 'SKILL.md' \
        -not -path '*/_shared/*' \
        2>/dev/null
    )
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_SKILL_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipes = {
    "body-length": os.environ["CHECK_SKILL_RECIPE_BODY_LENGTH"],
    "line-length": os.environ["CHECK_SKILL_RECIPE_LINE_LENGTH"],
}

per_rule = {"body-length": [], "line-length": []}
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 4)
    if len(parts) != 5:
        continue
    rule_id, status, path, lineno, context = parts
    if rule_id not in per_rule:
        continue
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    per_rule[rule_id].append(
        emit_json_finding(
            rule_id=rule_id,
            status=status,
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=f"{path} {context}.",
            recommended_changes=recipes[rule_id],
        )
    )

envelopes = [
    emit_rule_envelope(rule_id="body-length", findings=per_rule["body-length"]),
    emit_rule_envelope(rule_id="line-length", findings=per_rule["line-length"]),
]
print_envelope(envelopes)
if any(e["overall_status"] == "fail" for e in envelopes):
    sys.exit(1)
'

emit_envelopes() {
  CHECK_SKILL_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SKILL_RECIPE_BODY_LENGTH="${RECIPE_BODY_LENGTH}" \
    CHECK_SKILL_RECIPE_LINE_LENGTH="${RECIPE_LINE_LENGTH}" \
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
  local target
  local rc=0
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
