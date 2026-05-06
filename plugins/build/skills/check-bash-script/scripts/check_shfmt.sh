#!/usr/bin/env bash
#
# check_shfmt.sh — Deterministic Tier-1 format check for Bash scripts,
# wrapping the external `shfmt` tool. Emits JSON envelope per
# scripts/_common.py.
#
# Single-rule script: rule_id="format". Format drift is WARN (not blocking
# at Tier-1; coaching). `shfmt` is optional — when absent, this script
# emits an INFO-style envelope with overall_status="inapplicable" and
# exits 0, matching the Missing Tools preamble pattern.
#
# Format flags: `-i 2 -ci -bn` per the bash-script-best-practices.md
# style guidance (2-space indent, switch-case indent, binop on next line).
#
# Usage:
#   check_shfmt.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (overall_status pass / warn / inapplicable)
#   1   overall_status=fail (not produced — format drift is always WARN)
#   64  usage error
#   69  missing required dependency (not shfmt)

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(find basename head python3)

readonly SHFMT_FLAGS=(-i 2 -ci -bn)

readonly RECOMMEND_TEMPLATE='Run `shfmt -w -i 2 -ci -bn <file>` to apply the canonical layout (2-space indent, indented case patterns, binary operators on next line). CI gates drift via `shfmt -d`.'

usage() {
  cat <<'EOF'
check_shfmt.sh — shfmt format check for Bash scripts. Emits JSON.

Usage:
  check_shfmt.sh <path> [<path> ...]

shfmt is optional. When absent, an inapplicable envelope is emitted
and the script exits 0.

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   overall_status pass / warn / inapplicable
  1   overall_status fail (not produced by this script)
  64  usage error
  69  missing required dependency (not shfmt)
EOF
}

install_hint() {
  case "${1}" in
    find | basename | head) printf 'should be preinstalled on any POSIX system' ;;
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

# Collect files with format drift; print one path per stdout line.
check_one() {
  local target="$1"
  if shfmt "${SHFMT_FLAGS[@]}" -d "${target}" >/dev/null 2>&1; then
    return 0
  fi
  printf '%s\n' "${target}"
}

# Walk a path (file or top-level dir); emit one drifted-file path per line.
collect_drifted() {
  local target="$1"
  local file

  if [[ -f "${target}" ]]; then
    if is_bash_script "${target}"; then
      check_one "${target}"
    fi
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      if is_bash_script "${file}"; then
        check_one "${file}"
      fi
    done < <(
      find "${target}" -maxdepth 1 -type f \
        \( -name '*.sh' -o -name '*.bash' -o ! -name '*.*' \) 2>/dev/null
    )
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

# Pipe drifted-file paths to python3 + _common.py to build the JSON envelope.
readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_BASH_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

if os.environ["CHECK_BASH_STATUS"] == "missing":
    env = emit_rule_envelope("format", findings=[], inapplicable=True)
    print_envelope(env)
    sys.exit(0)

paths = [line.strip() for line in sys.stdin if line.strip()]
recipe = os.environ["CHECK_BASH_RECIPE"]
findings = [
    emit_json_finding(
        rule_id="format",
        status="warn",
        location={"line": 1, "context": p},
        reasoning=(
            f"shfmt -d reports format drift in {p}. "
            "Layout differs from `shfmt -i 2 -ci -bn` canonical."
        ),
        recommended_changes=recipe,
    )
    for p in paths
]
print_envelope(emit_rule_envelope("format", findings))
'

emit_envelope() {
  local status="$1" # "ok" | "missing"
  CHECK_BASH_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_BASH_RECIPE="${RECOMMEND_TEMPLATE}" \
    CHECK_BASH_STATUS="${status}" \
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

  if ! command -v shfmt >/dev/null 2>&1; then
    : | emit_envelope "missing"
    exit 0
  fi

  local target
  {
    for target in "$@"; do
      collect_drifted "${target}"
    done
  } | emit_envelope "ok"
  # set -o pipefail propagates collect_drifted's exit code (e.g., 64
  # for path-not-found) to the pipeline's exit; set -e then exits.
  exit 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
