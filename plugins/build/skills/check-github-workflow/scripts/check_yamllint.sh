#!/usr/bin/env bash
#
# check_yamllint.sh — Tier-1 wrapper for `yamllint`, catching YAML
# syntax errors and style issues that actionlint / zizmor may not.
#
# yamllint is optional — when absent, this script emits a single INFO
# line and exits 0, matching the Missing Tools contract.
#
# Usage:
#   check_yamllint.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (including when yamllint is absent)
#   1   one or more FAIL findings (not produced — yamllint output is WARN)
#   64  usage error

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

collect_targets() {
  local arg
  for arg in "$@"; do
    if [[ -d "${arg}" ]]; then
      find "${arg}" -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) -print0 | sort -z
    elif [[ -f "${arg}" ]]; then
      printf '%s\0' "${arg}"
    fi
  done
}

main() {
  if [[ $# -lt 1 ]]; then
    printf 'usage: %s <path> [<path> ...]\n' "${PROGNAME}" >&2
    exit 64
  fi

  if ! command -v yamllint >/dev/null 2>&1; then
    printf 'INFO     tool-missing: yamllint not installed — Tier-1 YAML style coverage reduced\n'
    printf '  Recommendation: Install via `pipx install yamllint` or the distribution package manager.\n'
    exit 0
  fi

  local -a targets=()
  local file
  while IFS= read -r -d '' file; do
    targets+=("${file}")
  done < <(collect_targets "$@")

  if [[ ${#targets[@]} -eq 0 ]]; then
    printf 'INFO     no workflow files found in provided paths\n'
    exit 0
  fi

  # yamllint `-f parsable` output: `<path>:<line>:<col>: [<level>] <message> (<rule>)`
  local output
  output="$(yamllint -f parsable "${targets[@]}" 2>&1 || true)"
  if [[ -z "${output}" ]]; then
    exit 0
  fi

  while IFS= read -r line; do
    if [[ "${line}" =~ ^([^:]+):([0-9]+):[0-9]+:\ \[([^]]+)\]\ (.+)$ ]]; then
      local path="${BASH_REMATCH[1]}"
      local lineno="${BASH_REMATCH[2]}"
      local level="${BASH_REMATCH[3]}"
      local message="${BASH_REMATCH[4]}"
      printf 'WARN     %s:%s — yaml-valid: [%s] %s\n' "${path}" "${lineno}" "${level}" "${message}"
      printf '  Recommendation: Apply the yamllint fix. Common: consistent indentation, no trailing whitespace, trailing newline.\n'
    fi
  done <<< "${output}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
