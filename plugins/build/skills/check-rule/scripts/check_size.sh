#!/usr/bin/env bash
#
# check_size.sh — Tier-1 file-size check for Claude Code rule files.
# Emits a JSON ARRAY with one envelope (rule_id="size") per
# scripts/_common.py.
#
# Counts non-blank lines per file; emits WARN at >200 and FAIL at >500.
# A "non-blank" line contains at least one non-whitespace character.
# Blank lines are excluded so formatting padding doesn't push a file
# past threshold.
#
# Usage:
#   check_size.sh <path> [<path> ...]
#
# Paths may be files or directories (recursively scanned for *.md).
#
# Exit codes:
#   0   no FAIL findings (overall_status pass / warn / inapplicable)
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

readonly WARN_THRESHOLD=200
readonly FAIL_THRESHOLD=500

readonly RECIPE_SIZE='Split the rule by topic and move long-form rationale out of `.claude/rules/`. Soft cap (>200 lines): split into topic-specific files (e.g., api-conventions.md + test-conventions.md). Hard cap (>500 lines): the file is a document, not a rule — split into rules AND move long-form explanation to `.context/<name>.md` or a CLAUDE.md section. Larger rules consume context and reduce adherence; splitting also improves the on-demand load path for path-scoped rules.'

usage() {
  cat <<'EOF'
check_size.sh — File-size check for Claude Code rule files.

Usage:
  check_size.sh <path> [<path> ...]

Thresholds:
  WARN  > 200 non-blank lines  ("prefer short" soft cap)
  FAIL  > 500 non-blank lines  (document-not-rule hard cap)

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

count_nonblank() {
  local file="$1"
  awk 'NF > 0 { n++ } END { print n+0 }' "${file}" 2>/dev/null || printf '0'
}

# Emit findings as TSV: <status>\t<file>\t<count>\t<threshold>
emit_raw() {
  local file="$1"
  local count
  count="$(count_nonblank "${file}")"

  if [[ "${count}" -gt "${FAIL_THRESHOLD}" ]]; then
    printf 'fail\t%s\t%s\t%s\n' "${file}" "${count}" "${FAIL_THRESHOLD}"
  elif [[ "${count}" -gt "${WARN_THRESHOLD}" ]]; then
    printf 'warn\t%s\t%s\t%s\n' "${file}" "${count}" "${WARN_THRESHOLD}"
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
    done < <(find "${target}" -type f -name '*.md' 2>/dev/null)
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_RULE_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipe = os.environ["CHECK_RULE_RECIPE_SIZE"]

findings = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 3)
    if len(parts) != 4:
        continue
    status, path, count, threshold = parts
    findings.append(
        emit_json_finding(
            rule_id="size",
            status=status,
            location={"line": 1, "context": f"{path}: {count} non-blank lines"},
            reasoning=(
                f"{path} has {count} non-blank lines, exceeding the "
                f"{threshold}-line threshold. Larger rules consume "
                "context and reduce adherence; at the hard cap the file "
                "is a document, not a rule."
            ),
            recommended_changes=recipe,
        )
    )

envelope = emit_rule_envelope(rule_id="size", findings=findings)
print_envelope([envelope])

if envelope["overall_status"] == "fail":
    sys.exit(1)
'

emit_envelopes() {
  CHECK_RULE_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_RULE_RECIPE_SIZE="${RECIPE_SIZE}" \
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
