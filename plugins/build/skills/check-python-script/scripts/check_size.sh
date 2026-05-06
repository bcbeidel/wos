#!/usr/bin/env bash
#
# check_size.sh — Deterministic Tier-1 size check for Python scripts.
# Emits a JSON ARRAY containing one envelope (rule_id="size") per
# scripts/_common.py.
#
# size (WARN): script length over 500 non-blank lines.
#
# Single-file scripts past ~500 non-blank lines are an anti-pattern —
# the convention is to graduate to a proper package.
#
# Usage:
#   check_size.sh <path> [<path> ...]
#
# Paths may be .py files or directories (top-level .py only; scripts
# are single-file by definition — no recursion into subpackages).
#
# Exit codes:
#   0   no FAIL findings (all findings are WARN)
#   1   one or more FAIL findings (not produced by this script)
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

readonly MAX_NON_BLANK_LINES=500

readonly _RULE_ORDER="size"

readonly RECIPE_SIZE='Extract cohesive sections into helper functions (or modules, if the refactor is large enough to justify a `<script>_helpers.py` alongside the script). Past ~500 non-blank lines, convert to a package: `pyproject.toml` + `src/<pkg>/`. Single-file discipline breaks down past a threshold; a 750-line script fails testability, readability, and partial-import signals that a package handles cleanly.'

usage() {
  cat <<EOF
check_size.sh — Flag Python scripts exceeding the size threshold.

Usage:
  check_size.sh <path> [<path> ...]

Check:
  size  WARN at > ${MAX_NON_BLANK_LINES} non-blank lines

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

# Count non-blank lines — blank = empty or whitespace-only.
non_blank_count() {
  awk 'NF { count++ } END { print count + 0 }' "$1"
}

# TSV: <rule_id>\t<status>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  local count
  count="$(non_blank_count "${file}")"
  if [[ "${count}" -gt "${MAX_NON_BLANK_LINES}" ]]; then
    printf 'size\twarn\t%s\t1\t%s non-blank lines (threshold %s)\n' \
      "${file}" "${count}" "${MAX_NON_BLANK_LINES}"
  fi
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    case "${target}" in
      *.py) emit_raw "${target}" ;;
    esac
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      emit_raw "${file}"
    done < <(find "${target}" -maxdepth 1 -type f -name '*.py' 2>/dev/null)
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_PY_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

order = os.environ["CHECK_PY_RULE_ORDER"].split(",")
recipes = {
    "size": os.environ["CHECK_PY_RECIPE_SIZE"],
}

per_rule = {r: [] for r in order}
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
  CHECK_PY_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_PY_RULE_ORDER="${_RULE_ORDER}" \
    CHECK_PY_RECIPE_SIZE="${RECIPE_SIZE}" \
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
