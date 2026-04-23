#!/usr/bin/env bash
#
# check_safety.sh — Deterministic Tier-1 safety checks for Bash
# scripts: `eval` flag, GNU-only flag detection, hardcoded `/tmp/`
# path literals.
#
# Three checks, each FAIL or WARN:
#   eval         FAIL — flag any `eval` invocation lacking a justification comment
#   gnu-flags    WARN — flag GNU-only flags without a declared dependency comment
#   tmp-literal  FAIL — flag string literals starting with /tmp/ or /var/tmp/
#
# Justification comments accepted for `eval`:
#   `# shellcheck disable=SC2294 ...`
#   `# eval-justified: <reason>`
#
# Justification comment accepted for GNU flags:
#   `# requires: gnu-coreutils` (anywhere in the file's first 20 lines)
#
# Usage:
#   check_safety.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

readonly REQUIRED_CMDS=(awk find basename head grep)

usage() {
  # eval-justified: word appears in help text below, not as an invocation
  cat <<'EOF'
check_safety.sh — Bash safety checks: eval-use, GNU flags, tmp literals.

Usage:
  check_safety.sh <path> [<path> ...]

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
    awk | find | basename | head | grep) printf 'should be preinstalled on any POSIX system' ;;
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

is_bash_script() {
  local file="$1"
  case "${file}" in
    *.sh | *.bash) return 0 ;;
  esac
  local first
  first="$(head -n 1 "${file}" 2>/dev/null || true)"
  case "${first}" in
    "#!/usr/bin/env bash" | "#!/bin/bash" | "#!/usr/bin/env -S bash"*) return 0 ;;
  esac
  return 1
}

check_eval() {
  local file="$1"
  local fail=0
  # Find every `eval ` (word-bounded). For each, check whether the same
  # line or the immediately prior line carries a justification comment.
  local lineno
  while IFS= read -r lineno; do
    local this_line prev_line
    this_line="$(awk -v n="${lineno}" 'NR == n' "${file}")"
    prev_line="$(awk -v n="$((lineno - 1))" 'NR == n' "${file}")"
    if [[ "${this_line}" == *"shellcheck disable=SC2294"* ]] \
      || [[ "${this_line}" == *"eval-justified:"* ]] \
      || [[ "${prev_line}" == *"shellcheck disable=SC2294"* ]] \
      || [[ "${prev_line}" == *"eval-justified:"* ]]; then
      continue
    fi
    # eval-justified: following printf lines are user-facing finding/recommendation text
    printf 'FAIL  %s — eval: line %s uses `eval` without justification comment\n' \
      "${file}" "${lineno}"
    # eval-justified: word appears in recommendation message, not as a bash invocation
    printf '  Recommendation: Replace eval with case dispatch, parameter expansion, or array call. '
    printf 'If required, add # shellcheck disable=SC2294 or # eval-justified comment.\n'
    fail=1
  done < <(awk '
    /^[[:space:]]*#/ { next }
    /(^|[[:space:]]|;|\(|`)eval[[:space:]]/ { print NR }
  ' "${file}")
  return "${fail}"
}

check_gnu_flags() {
  local file="$1"
  # Skip the check if the file declares the dependency in the first 20 lines.
  if head -n 20 "${file}" | grep -qiE 'requires:[[:space:]]*gnu-coreutils'; then
    return 0
  fi
  local emitted=0
  while IFS=: read -r lineno match; do
    if [[ "${emitted}" -ge 3 ]]; then
      break
    fi
    printf 'WARN  %s — gnu-flags: line %s uses GNU-only flag (%s)\n' \
      "${file}" "${lineno}" "${match}"
    printf '  Recommendation: Either declare `# requires: gnu-coreutils` in the header, '
    printf 'or use a portable form (e.g., `sed -e ... > out && mv out file` instead of `sed -i`).\n'
    emitted=$((emitted + 1))
  done < <(awk '
    /^[[:space:]]*#/ { next }
    /sed[[:space:]]+-i[[:space:]]/ && !/sed[[:space:]]+-i[[:space:]]+["'"'"']/ {
      printf "%d:sed -i (no backup arg, GNU-only)\n", NR; next
    }
    /grep[[:space:]]+(-[a-zA-Z]*)?P/ { printf "%d:grep -P\n", NR; next }
    /readlink[[:space:]]+-f/ { printf "%d:readlink -f\n", NR; next }
    /[^a-zA-Z]date[[:space:]]+-d[[:space:]]/ { printf "%d:date -d\n", NR; next }
    /stat[[:space:]]+-c[[:space:]]/ { printf "%d:stat -c\n", NR; next }
    /xargs[[:space:]]+(-[a-zA-Z]*)?r/ { printf "%d:xargs -r\n", NR; next }
  ' "${file}")
}

check_tmp_literal() {
  local file="$1"
  local fail=0
  while IFS=: read -r lineno _; do
    printf 'FAIL  %s — tmp-literal: line %s has hardcoded /tmp or /var/tmp literal\n' \
      "${file}" "${lineno}"
    printf '  Recommendation: Use `mktemp` (or `mktemp -d`) and pair with `trap` cleanup.\n'
    fail=1
  done < <(awk '
    /^[[:space:]]*#/ { next }
    /["'"'"'](\/tmp|\/var\/tmp)\// { printf "%d:1\n", NR }
  ' "${file}")
  return "${fail}"
}

check_file() {
  local file="$1"
  local fail=0
  check_eval "${file}" || fail=1
  check_gnu_flags "${file}"
  check_tmp_literal "${file}" || fail=1
  return "${fail}"
}

check_path() {
  local target="$1"
  local any=0
  local file

  if [[ -f "${target}" ]]; then
    if is_bash_script "${target}"; then
      check_file "${target}" || any=1
    fi
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      if is_bash_script "${file}"; then
        check_file "${file}" || any=1
      fi
    done < <(
      find "${target}" -maxdepth 1 -type f \
        \( -name '*.sh' -o -name '*.bash' -o ! -name '*.*' \) 2>/dev/null
    )
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
  return "${any}"
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

  local any=0
  local target
  for target in "$@"; do
    check_path "${target}" || any=1
  done

  exit "${any}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
