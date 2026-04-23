#!/usr/bin/env bash
#
# check_idioms.sh — Deterministic Tier-1 idiom checks for Bash scripts:
# `[[ ]]` over `[ ]`, `printf` over `echo` for non-trivial output,
# `${var}` braces when adjacent to identifier-shaped text.
#
# All findings are WARN (idioms are style-coding, not correctness bugs).
#
# Usage:
#   check_idioms.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (WARN exits 0)
#   1   one or more FAIL findings (not produced by this script)
#   64  usage error
#   69  missing dependency

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"

REQUIRED_CMDS=(awk find basename head)

usage() {
  cat <<'EOF'
check_idioms.sh — Bash idiom checks (style-level WARN findings).

Usage:
  check_idioms.sh <path> [<path> ...]

Checks:
  bracket-test       `[[ ]]` over `[ ]` for tests in bash files
  printf-over-echo   `printf` over `echo` for non-trivial output
  var-braces         `${var}` braces when expansion abuts identifier text

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

check_bracket_test() {
  local file="$1"
  # Match `[ ` after `if`, `elif`, `while`, `until`, `&&`, `||`, or at
  # the start of a logical block. Skip [[ ]] (already correct) and skip
  # `[ -L "$x" ]`-style POSIX-only patterns which are still valid bash.
  # Heuristic: emit WARN per file, capped at 3.
  local emitted=0
  while IFS=: read -r lineno _; do
    if [ "${emitted}" -ge 3 ]; then
      break
    fi
    printf 'WARN  %s — bracket-test: line %s uses `[ ... ]`; prefer `[[ ... ]]` in bash\n' \
      "${file}" "${lineno}"
    printf '  Recommendation: Replace `[ ... ]` with `[[ ... ]]` — no word-splitting, supports pattern matching.\n'
    emitted=$((emitted + 1))
  done < <(awk '
    # Skip comments
    /^[[:space:]]*#/ { next }
    # Match `[ ` not preceded by `[`
    /(^|[[:space:]]|[;&|])\[[[:space:]]/ {
      # Exclude lines that already have [[
      if ($0 !~ /\[\[/) {
        printf "%d:1\n", NR
      }
    }
  ' "${file}")
}

check_printf_over_echo() {
  local file="$1"
  # Flag `echo -e`, `echo -n`, or echo with backslash escapes — these
  # are the cases printf handles more portably. Skip plain `echo "literal"`.
  local emitted=0
  while IFS=: read -r lineno _; do
    if [ "${emitted}" -ge 3 ]; then
      break
    fi
    printf 'WARN  %s — printf-over-echo: line %s uses `echo` with flags or escapes; prefer `printf`\n' \
      "${file}" "${lineno}"
    printf '  Recommendation: Replace `echo -e/-n/escapes` with `printf` for portable output.\n'
    emitted=$((emitted + 1))
  done < <(awk '
    /^[[:space:]]*#/ { next }
    /[^a-zA-Z0-9_]echo[[:space:]]+(-[en]|-[en][en])/ ||
    /[^a-zA-Z0-9_]echo[[:space:]].*\\[ntr\\]/ {
      printf "%d:1\n", NR
    }
  ' "${file}")
}

check_var_braces() {
  local file="$1"
  # Flag `$varfoo`-style adjacency where `$var` is followed by characters
  # that could be part of an identifier. This is a heuristic — false
  # positives possible. Cap at 3 per file.
  local emitted=0
  while IFS=: read -r lineno _; do
    if [ "${emitted}" -ge 3 ]; then
      break
    fi
    printf 'WARN  %s — var-braces: line %s has `$var` adjacent to identifier text; use `${var}` braces\n' \
      "${file}" "${lineno}"
    printf '  Recommendation: Use `${var}` when the expansion abuts characters that could be part of an identifier.\n'
    emitted=$((emitted + 1))
  done < <(awk '
    /^[[:space:]]*#/ { next }
    # Match $name followed by [a-zA-Z0-9_] without preceding ${
    {
      line = $0
      while (match(line, /\$[a-zA-Z_][a-zA-Z0-9_]*[a-zA-Z0-9_]/)) {
        # Pull the matched substring
        m = substr(line, RSTART, RLENGTH)
        # The match must end with an identifier char that is part of a longer run
        # i.e. $varfoo where "foo" continues identifier-shaped chars
        # We detect: after $name part, there is more identifier char to consume
        # awk regex matched at least one trailing identifier char; emit.
        printf "%d:1\n", NR
        line = substr(line, RSTART + RLENGTH)
        break  # one finding per line
      }
    }
  ' "${file}")
}

check_file() {
  local file="$1"
  check_bracket_test "${file}"
  check_printf_over_echo "${file}"
  check_var_braces "${file}"
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
