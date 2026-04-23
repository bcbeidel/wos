#!/usr/bin/env bash
#
# check_structure.sh — Deterministic Tier-1 structural checks for
# Bash 4.0+ scripts: shebang form, strict-mode prologue, header
# comment, main function, sourceable guard, readonly constants,
# mktemp/trap pairing.
#
# Usage:
#   check_structure.sh <path> [<path> ...]
#
# Paths may be .sh files or directories (top-level only).
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, find, basename, head, grep

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

readonly REQUIRED_CMDS=(awk find basename head grep)

usage() {
  cat <<'EOF'
check_structure.sh — Structural checks for Bash 4.0+ scripts.

Usage:
  check_structure.sh <path> [<path> ...]

Checks:
  shebang             first line is #!/usr/bin/env bash or #!/bin/bash
  strict-mode         set -euo pipefail in first ~20 non-comment lines
  header-comment      comment block in first 10 lines naming purpose/usage
  main-fn             a `main` function is defined
  main-guard          [[ "${BASH_SOURCE[0]}" == "$0" ]] guard at module bottom
  readonly-config     top-level constants declared with `readonly`
  mktemp-trap         every mktemp-call is preceded by a trap registration

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

check_shebang() {
  local file="$1"
  local first
  first="$(head -n 1 "${file}")"
  case "${first}" in
    "#!/usr/bin/env bash" | "#!/bin/bash" | "#!/usr/bin/env -S bash"*)
      return 0
      ;;
    *)
      printf 'FAIL  %s — shebang: first line is %q, expected a bash shebang\n' \
        "${file}" "${first}"
      printf "  Recommendation: Replace the first line with '#!/usr/bin/env bash'.\n"
      return 1
      ;;
  esac
}

check_strict_mode() {
  local file="$1"
  # Look for set -euo pipefail (or equivalent) in first 20 non-comment, non-blank lines.
  if awk '
    /^[[:space:]]*$/ || /^[[:space:]]*#/ { next }
    { count++ }
    /set[[:space:]]+-[Ee]?[Eaeux]*o?[[:space:]]+pipefail/ ||
    /set[[:space:]]+-o[[:space:]]+errexit/ { found=1 }
    count >= 20 { exit }
    END { exit found ? 0 : 1 }
  ' "${file}"; then
    return 0
  fi
  printf 'FAIL  %s — strict-mode: `set -euo pipefail` not found in prologue\n' "${file}"
  printf '  Recommendation: Add `set -euo pipefail` immediately after the shebang.\n'
  return 1
}

check_header_comment() {
  local file="$1"
  # First 10 lines should contain at least 3 comment lines (excluding shebang).
  local comment_count
  comment_count="$(
    awk 'NR > 1 && NR <= 10 && /^[[:space:]]*#/ { count++ } END { print count + 0 }' \
      "${file}"
  )"
  if [[ "${comment_count}" -lt 3 ]]; then
    printf 'WARN  %s — header-comment: no purpose/usage block in first 10 lines\n' "${file}"
    printf '  Recommendation: Add a header block: purpose, usage, deps, exit codes.\n'
  fi
}

check_main_fn() {
  local file="$1"
  if ! grep -qE '^(function[[:space:]]+)?main[[:space:]]*\(\)' "${file}"; then
    printf 'WARN  %s — main-fn: no `main` function defined\n' "${file}"
    printf '  Recommendation: Wrap execution in main() and call from the sourceable guard.\n'
  fi
}

check_main_guard() {
  local file="$1"
  local pattern='\$\{BASH_SOURCE\[0\]\}.*==.*\$\{?0\}?|\$\{?0\}?.*==.*\$\{BASH_SOURCE\[0\]\}'
  if ! grep -qE "${pattern}" "${file}"; then
    printf 'WARN  %s — main-guard: missing BASH_SOURCE-equals-0 sourceable guard\n' "${file}"
    printf "  Recommendation: Add the canonical BASH_SOURCE guard calling main at EOF.\n"
  fi
}

check_readonly_config() {
  local file="$1"
  # Heuristic: if there are ≥2 top-level UPPERCASE assignments and zero `readonly` declarations,
  # suggest readonly. Top-level = no leading whitespace, not inside a function.
  local upper_assigns readonly_decls
  upper_assigns="$(awk '
    /^[[:space:]]/ { next }
    /^[A-Z][A-Z0-9_]+=/ { count++ }
    END { print count + 0 }
  ' "${file}")"
  readonly_decls="$(grep -cE '^readonly[[:space:]]' "${file}" 2>/dev/null || true)"
  if [[ "${upper_assigns}" -ge 2 ]] && [[ "${readonly_decls}" -eq 0 ]]; then
    printf 'WARN  %s — readonly-config: top-level UPPERCASE constants not readonly\n' "${file}"
    printf '  Recommendation: Declare top-level constants readonly to prevent reassignment.\n'
  fi
}

check_mktemp_trap() {
  local file="$1"
  # If mktemp is used, require a `trap ... EXIT` somewhere before the first mktemp.
  local first_mktemp first_trap
  first_mktemp="$(awk '
    /^[[:space:]]*#/ { next }
    /(^|[[:space:]]|;|\|)mktemp([[:space:]]|$)/ { print NR; exit }
  ' "${file}")"
  if [[ -z "${first_mktemp}" ]]; then
    return 0
  fi
  first_trap="$(awk '/^[[:space:]]*trap[[:space:]].*EXIT/ { print NR; exit }' "${file}")"
  if [[ -z "${first_trap}" ]] || [[ "${first_trap}" -gt "${first_mktemp}" ]]; then
    printf 'WARN  %s — mktemp-trap-pairing: mktemp-call at line %s with no prior trap EXIT\n' \
      "${file}" "${first_mktemp}"
    printf "  Recommendation: Install a trap EXIT INT TERM before the mktemp-call.\n"
  fi
}

check_file() {
  local file="$1"
  local fail=0
  check_shebang "${file}" || fail=1
  check_strict_mode "${file}" || fail=1
  check_header_comment "${file}"
  check_main_fn "${file}"
  check_main_guard "${file}"
  check_readonly_config "${file}"
  check_mktemp_trap "${file}"
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
