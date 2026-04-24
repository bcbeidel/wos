#!/usr/bin/env bash
#
# check_actionlint.sh — Tier-1 wrapper for `actionlint`, the canonical
# GitHub Actions workflow schema / expression / shellcheck-integrated
# linter.
#
# actionlint is optional — when absent, this script emits a single INFO
# line and exits 0, matching the Missing Tools contract used by the
# other optional-tool wrappers in this skill.
#
# Usage:
#   check_actionlint.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (including when actionlint is absent)
#   1   one or more FAIL findings (not produced — actionlint output is WARN)
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
  local -a out=()
  local arg
  for arg in "$@"; do
    if [[ -d "${arg}" ]]; then
      while IFS= read -r -d '' file; do
        out+=("${file}")
      done < <(find "${arg}" -maxdepth 1 -type f \( -name '*.yml' -o -name '*.yaml' \) -print0 | sort -z)
    elif [[ -f "${arg}" ]]; then
      out+=("${arg}")
    fi
  done
  if [[ ${#out[@]} -gt 0 ]]; then
    printf '%s\n' "${out[@]}"
  fi
}

main() {
  if [[ $# -lt 1 ]]; then
    printf 'usage: %s <path> [<path> ...]\n' "${PROGNAME}" >&2
    exit 64
  fi

  if ! command -v actionlint >/dev/null 2>&1; then
    printf 'INFO     tool-missing: actionlint not installed — Tier-1 workflow-schema coverage reduced\n'
    printf '  Recommendation: Install via `brew install actionlint` (macOS) or `go install github.com/rhysd/actionlint/cmd/actionlint@latest`.\n'
    exit 0
  fi

  local -a targets=()
  local file
  while IFS= read -r file; do
    targets+=("${file}")
  done < <(collect_targets "$@")

  if [[ ${#targets[@]} -eq 0 ]]; then
    printf 'INFO     no workflow files found in provided paths\n'
    exit 0
  fi

  # actionlint `-no-color` keeps output parseable. Exit is 0 = clean,
  # 1 = findings, 2 = fatal error. We translate findings to WARN without
  # propagating the non-zero exit.
  local output
  output="$(actionlint -no-color "${targets[@]}" 2>&1 || true)"
  if [[ -z "${output}" ]]; then
    exit 0
  fi

  # actionlint lines: <path>:<line>:<col>: <message> [<rule>]
  while IFS= read -r line; do
    if [[ "${line}" =~ ^([^:]+):([0-9]+):[0-9]+:\ (.+)$ ]]; then
      local path="${BASH_REMATCH[1]}"
      local lineno="${BASH_REMATCH[2]}"
      local message="${BASH_REMATCH[3]}"
      printf 'WARN     %s:%s — actionlint: %s\n' "${path}" "${lineno}" "${message}"
      printf '  Recommendation: See https://github.com/rhysd/actionlint/blob/main/docs/checks.md for the rule.\n'
    elif [[ -n "${line// }" ]]; then
      # Context lines from actionlint (snippets, carets) — skip.
      continue
    fi
  done <<< "${output}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
