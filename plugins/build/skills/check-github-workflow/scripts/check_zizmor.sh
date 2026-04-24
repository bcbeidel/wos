#!/usr/bin/env bash
#
# check_zizmor.sh — Tier-1 wrapper for `zizmor`, a static-analysis
# auditor for GitHub Actions workflows focused on supply-chain and
# security anti-patterns (unpinned-uses, excessive-permissions,
# template-injection, dangerous-triggers, self-hosted-runner, etc.).
#
# zizmor is optional — when absent, this script emits a single INFO
# line and exits 0, matching the Missing Tools contract.
#
# Usage:
#   check_zizmor.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (including when zizmor is absent)
#   1   one or more FAIL findings (not produced — zizmor output is WARN)
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

  if ! command -v zizmor >/dev/null 2>&1; then
    printf 'INFO     tool-missing: zizmor not installed — Tier-1 supply-chain / security coverage reduced\n'
    printf '  Recommendation: Install via `pipx install zizmor` or `brew install zizmor` (macOS).\n'
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

  # zizmor plaintext output — stable format: one line per finding,
  # `<severity> <path>:<line>:<col>: <rule>: <message>` approximately.
  # We re-emit as WARN regardless of zizmor's severity since zizmor's
  # FAIL-class findings overlap with check_pinning.py / check_safety.py
  # and are deduplicated by the orchestrator.
  local output
  output="$(zizmor --no-color --format plain "${targets[@]}" 2>&1 || true)"
  if [[ -z "${output}" ]]; then
    exit 0
  fi

  while IFS= read -r line; do
    # Match `<severity> rule at <path>:<line>:<col>`
    if [[ "${line}" =~ ^([a-z]+):\ .+at\ ([^:]+):([0-9]+) ]]; then
      local path="${BASH_REMATCH[2]}"
      local lineno="${BASH_REMATCH[3]}"
      printf 'WARN     %s:%s — zizmor: %s\n' "${path}" "${lineno}" "${line}"
      printf '  Recommendation: See https://docs.zizmor.sh/audits/ for rule details.\n'
    elif [[ "${line}" =~ ^([^:]+\.ya?ml):([0-9]+):[0-9]+:\ (.+)$ ]]; then
      local path="${BASH_REMATCH[1]}"
      local lineno="${BASH_REMATCH[2]}"
      local message="${BASH_REMATCH[3]}"
      printf 'WARN     %s:%s — zizmor: %s\n' "${path}" "${lineno}" "${message}"
      printf '  Recommendation: See https://docs.zizmor.sh/audits/ for rule details.\n'
    fi
  done <<< "${output}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
