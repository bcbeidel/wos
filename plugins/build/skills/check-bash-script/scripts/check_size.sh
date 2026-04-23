#!/usr/bin/env bash
#
# check_size.sh — Deterministic Tier-1 size + line-length check for
# Bash scripts.
#
# Bash's lack of data structures and error handling stops scaling past
# ~300 non-blank lines; this check emits a WARN at the threshold.
# Per-line length is also flagged at >100 chars per Google Shell Style
# Guide convention. Both findings are WARN (no FAIL — line counts are
# heuristics, not correctness bugs).
#
# Usage:
#   check_size.sh <path> [<path> ...]
#
# Paths may be .sh files or directories (top-level only).
#
# Exit codes:
#   0   no FAIL findings (WARN exits 0 per the Tier-1 contract)
#   1   one or more FAIL findings (not produced by this script)
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, find, basename, head

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"

MAX_NON_BLANK_LINES=300
MAX_LINE_LENGTH=100

REQUIRED_CMDS=(awk find basename head)

usage() {
  cat <<'EOF'
check_size.sh — Flag Bash scripts exceeding size or line-length thresholds.

Usage:
  check_size.sh <path> [<path> ...]

Arguments:
  <path>   A .sh file or directory to scan (top-level files only).

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings
  1   one or more FAIL findings (not produced by this script)
  64  usage error
  69  missing dependency
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

non_blank_count() {
  awk 'NF { count++ } END { print count + 0 }' "$1"
}

check_file() {
  local file="$1"
  local count
  count="$(non_blank_count "${file}")"
  if [ "${count}" -gt "${MAX_NON_BLANK_LINES}" ]; then
    printf 'WARN  %s — size: %s non-blank lines (threshold %s)\n' \
      "${file}" "${count}" "${MAX_NON_BLANK_LINES}"
    printf '  Recommendation: Extract sections into helper scripts '
    printf '(source from a smaller orchestrator), or rewrite in Python '
    printf 'via /build:build-python-script.\n'
  fi

  # Per-line length WARN — emit at most 3 per file to avoid noise.
  local emitted=0
  while IFS=: read -r lineno length; do
    if [ "${emitted}" -ge 3 ]; then
      break
    fi
    printf 'WARN  %s — line-length: line %s is %s chars (threshold %s)\n' \
      "${file}" "${lineno}" "${length}" "${MAX_LINE_LENGTH}"
    printf '  Recommendation: Break with backslash continuation or extract a helper.\n'
    emitted=$((emitted + 1))
  done < <(awk -v max="${MAX_LINE_LENGTH}" '
    length($0) > max { printf "%d:%d\n", NR, length($0) }
  ' "${file}")
}

check_path() {
  local target="$1"
  local file

  if [ -f "${target}" ]; then
    if is_bash_script "${target}"; then
      check_file "${target}"
    fi
  elif [ -d "${target}" ]; then
    while IFS= read -r file; do
      if is_bash_script "${file}"; then
        check_file "${file}"
      fi
    done < <(find "${target}" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.bash' -o ! -name '*.*' \) 2>/dev/null)
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
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

  local target
  for target in "$@"; do
    check_path "${target}" || exit "$?"
  done

  exit 0
}

if [ "${0}" = "${BASH_SOURCE[0]:-$0}" ]; then
  main "$@"
fi
