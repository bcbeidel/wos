#!/usr/bin/env bash
#
# check_shellcheck.sh — Deterministic Tier-1 lint check for Bash
# scripts, wrapping the external `shellcheck` tool and reshaping its
# output to the fixed lint format.
#
# `shellcheck` is optional — when absent, this script emits a single
# INFO line naming the reduced coverage and exits 0, matching peer
# `check_ruff.sh`'s Missing Tools preamble pattern. Other Tier-1
# scripts continue running.
#
# Covers (severity → ShellCheck rule code):
#   FAIL: SC2086, SC2046, SC2068 (unquoted expansions)
#   FAIL: SC2294 (eval of array)
#   FAIL: SC2010, SC2012, SC2045 (parsing `ls`)
#   WARN: SC2154 (referenced but not assigned)
#   WARN: SC2155 (function var without local)
#   WARN: SC2006 (backticks)
#   WARN: SC2013, SC2162 (`for in $(cat)`)
#   WARN: SC2038 (`find | xargs` no -print0)
#   WARN: SC2164 (`cd` no exit)
#   WARN: SC2002 (useless cat)
#
# Usage:
#   check_shellcheck.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (including when shellcheck is absent)
#   1   one or more FAIL findings
#   64  usage error
#   69  missing required dependency (not shellcheck)

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"

REQUIRED_CMDS=(awk find basename head)

# Rule codes that escalate to FAIL; everything else is WARN.
FAIL_CODES="SC2086 SC2046 SC2068 SC2294 SC2010 SC2012 SC2045"

# The explicit selector set — kept in lockstep with the FAIL_CODES list
# and the audit-dimensions.md severity column.
SHELLCHECK_INCLUDE="SC2086,SC2046,SC2068,SC2154,SC2155,SC2006,SC2010,SC2012,SC2045,SC2013,SC2162,SC2038,SC2164,SC2002,SC2294"

usage() {
  cat <<'EOF'
check_shellcheck.sh — ShellCheck-backed lint check for Bash scripts.

Usage:
  check_shellcheck.sh <path> [<path> ...]

ShellCheck is optional. When absent, one INFO line is emitted naming
the reduced coverage and the script exits 0.

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings
  1   one or more FAIL findings
  64  usage error
  69  missing required dependency (not shellcheck)
EOF
}

install_hint() {
  case "${1}" in
    awk|find|basename|head) printf 'should be preinstalled on any POSIX system' ;;
    *)                      printf 'see your package manager' ;;
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
  if [ "${#missing[@]}" -gt 0 ]; then
    for cmd in "${missing[@]}"; do
      printf '%s: missing required command %q. Install: %s\n' \
        "${PROGNAME}" "${cmd}" "$(install_hint "${cmd}")" >&2
    done
    exit 69
  fi
}

severity_for() {
  local code="$1"
  case " ${FAIL_CODES} " in
    *" ${code} "*) printf 'FAIL' ;;
    *)             printf 'WARN' ;;
  esac
}

recommend_for() {
  case "$1" in
    SC2086|SC2046) printf 'Quote the expansion: "$var" or "$(cmd)".' ;;
    SC2068)        printf 'Use "$@" to forward arguments — never unquoted $@.' ;;
    SC2294)        printf 'Replace `eval "${arr[@]}"` with `"${arr[@]}"` — invoking the array directly.' ;;
    SC2154)        printf 'Either assign the variable, add a default `${var:-x}`, or guard with `${var:?msg}`.' ;;
    SC2155)        printf 'Split: `local x` then `x="$(cmd)"` to preserve the substitution exit status.' ;;
    SC2006)        printf 'Replace backticks with $(...) — nestable and readable.' ;;
    SC2010|SC2012|SC2045) printf 'Do not parse ls output — use globs or `find -print0 | xargs -0`.' ;;
    SC2013|SC2162) printf 'Use `while IFS= read -r line; do ...; done < file` for line iteration.' ;;
    SC2038)        printf 'Use `find ... -print0 | xargs -0 ...` (or `-exec ... {} +`) for filename safety.' ;;
    SC2164)        printf 'Add `|| exit` after `cd`, or rely on `set -e` and document.' ;;
    SC2002)        printf 'Pipe directly: `cmd file` instead of `cat file | cmd` (style; suppress with comment if intentional).' ;;
    *)             printf 'See https://www.shellcheck.net/wiki/%s for details.' "$1" ;;
  esac
}

is_bash_script() {
  local file="$1"
  case "${file}" in
    *.sh|*.bash) return 0 ;;
  esac
  local first
  first="$(head -n 1 "${file}" 2>/dev/null || true)"
  case "${first}" in
    "#!/usr/bin/env bash"|"#!/bin/bash"|"#!/usr/bin/env -S bash"*) return 0 ;;
  esac
  return 1
}

check_one() {
  local target="$1"
  local any=0
  local line

  # ShellCheck output (gcc format): `<path>:<line>:<col>: <severity>: <message> [<code>]`
  while IFS= read -r line; do
    case "${line}" in
      "") continue ;;
    esac
    # Extract path, line, col, message, code via a single awk pass.
    local path lineno col message code severity
    path="$(printf '%s' "${line}" | awk -F: '{print $1}')"
    lineno="$(printf '%s' "${line}" | awk -F: '{print $2}')"
    col="$(printf '%s' "${line}" | awk -F: '{print $3}')"
    message="$(printf '%s' "${line}" | awk -F: '{for (i=5; i<=NF; i++) printf "%s%s", $i, (i==NF?"":":")}')"
    code="$(printf '%s' "${message}" | awk -F'[][]' '{print $(NF-1)}')"
    case "${code}" in
      SC*) ;;
      *) continue ;;  # unrecognized line shape
    esac
    severity="$(severity_for "${code}")"
    printf '%s  %s — %s: %s (line %s:%s)\n' \
      "${severity}" "${path}" "${code}" "${message# }" "${lineno}" "${col}"
    printf '  Recommendation: %s\n' "$(recommend_for "${code}")"
    if [ "${severity}" = "FAIL" ]; then
      any=1
    fi
  done < <(shellcheck --include="${SHELLCHECK_INCLUDE}" --format=gcc "${target}" 2>/dev/null || true)

  return "${any}"
}

check_path() {
  local target="$1"
  local any=0
  local file

  if [ -f "${target}" ]; then
    if is_bash_script "${target}"; then
      check_one "${target}" || any=1
    fi
  elif [ -d "${target}" ]; then
    while IFS= read -r file; do
      if is_bash_script "${file}"; then
        check_one "${file}" || any=1
      fi
    done < <(find "${target}" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.bash' -o ! -name '*.*' \) 2>/dev/null)
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
  return "${any}"
}

main() {
  if [ "$#" -eq 0 ]; then
    usage >&2
    exit 64
  fi

  case "${1:-}" in
    -h|--help) usage; exit 0 ;;
  esac

  preflight

  if ! command -v shellcheck >/dev/null 2>&1; then
    printf 'INFO  <shellcheck> — tool-missing: shellcheck not installed; 15 rule codes skipped\n'
    printf "  Recommendation: Install shellcheck — 'brew install shellcheck' (macOS), "
    printf "'apt install shellcheck' (Debian/Ubuntu), 'dnf install ShellCheck' (Fedora).\n"
    exit 0
  fi

  local any=0
  local target
  for target in "$@"; do
    check_path "${target}" || any=1
  done

  exit "${any}"
}

if [ "${0}" = "${BASH_SOURCE[0]:-$0}" ]; then
  main "$@"
fi
