#!/usr/bin/env bash
#
# check_checkmake.sh — Tier-1 wrapper around `checkmake`. Emits JSON
# envelope per scripts/_common.py.
#
# `checkmake` (https://github.com/mrtazz/checkmake) catches Make-idiom
# mistakes that regex checks miss: mixed phony / file-target prerequisites,
# expanded timestamps, oversize recipe bodies, and more. Single-rule
# script: rule_id="checkmake". Findings are WARN — coaching, not blocking.
#
# `checkmake` is OPTIONAL. When the tool is absent on PATH, this script
# emits a single envelope with overall_status="inapplicable" and exits 0
# so the audit continues. The `inapplicable` envelope is the user's
# signal that coverage is reduced.
#
# Usage:
#   check_checkmake.sh <path> [<path> ...]
#
# Exit codes:
#   0   overall_status pass / warn / inapplicable
#   1   overall_status=fail (not produced — checkmake findings are WARN)
#   64  usage error
#   69  missing required dependency (not checkmake)

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename python3)

readonly RECIPE_CHECKMAKE='Apply the rule-specific fix per checkmake (`checkmake --list-rules`):
  - MIXDEPS: split file and phony prerequisites into separate target lines.
  - TIMESTAMP_EXPANDED: quote timestamps so `$$(date)` is shell-evaluated, not Make-expanded.
  - MIN_PHONY: declare phony targets in `.PHONY:` (one rule per .PHONY block is fine).
  - MAX_BODY_LENGTH: extract the recipe body into `scripts/<name>.sh` and invoke it from the target.
Treat checkmake output as authoritative for the rules it covers.'

usage() {
  cat <<'EOF'
check_checkmake.sh — Wrap `checkmake` for Tier-1 Makefile audits. Emits JSON.

Usage:
  check_checkmake.sh <path> [<path> ...]

Arguments:
  <path>   A Makefile / GNUmakefile / *.mk file or directory (top-level).

Options:
  -h, --help   Show this help and exit.

`checkmake` is optional. When absent, an inapplicable envelope is emitted
and the script exits 0.

Exit codes:
  0   overall_status pass / warn / inapplicable
  1   overall_status fail (not produced by this script)
  64  usage error
  69  missing required dependency (not checkmake)
EOF
}

install_hint() {
  case "${1}" in
    awk | find | basename) printf 'should be preinstalled on any POSIX system' ;;
    python3) printf 'install Python 3.9+' ;;
    checkmake)
      printf '`brew install checkmake` (macOS) '
      printf 'or `go install github.com/mrtazz/checkmake@latest`'
      ;;
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

is_makefile() {
  local file="$1"
  local base
  base="$(basename "${file}")"
  case "${base}" in
    Makefile | GNUmakefile) return 0 ;;
    *.mk) return 0 ;;
  esac
  return 1
}

# Collect checkmake findings; emit one TSV record per finding:
#   <file>\t<line>\t<context>
# checkmake's default output is `rulename: detail` (sometimes prefixed
# with `<file>:`). We forward the stripped string as the context.
collect_findings() {
  local target="$1"
  local file
  local output
  local line
  local stripped

  scan_one() {
    local f="$1"
    if ! output="$(checkmake "${f}" 2>&1)"; then
      while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        stripped="${line#"${f}":}"
        printf '%s\t1\t%s\n' "${f}" "${stripped}"
      done <<<"${output}"
    fi
  }

  if [[ -f "${target}" ]]; then
    if is_makefile "${target}"; then
      scan_one "${target}"
    fi
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      if is_makefile "${file}"; then
        scan_one "${file}"
      fi
    done < <(
      find "${target}" -maxdepth 1 -type f \
        \( -name 'Makefile' -o -name 'GNUmakefile' -o -name '*.mk' \) 2>/dev/null
    )
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

# Pipe TSV findings to python3 + _common.py to build the JSON envelope.
readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_MAKEFILE_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

if os.environ["CHECK_MAKEFILE_STATUS"] == "missing":
    env = emit_rule_envelope("checkmake", findings=[], inapplicable=True)
    print_envelope(env)
    sys.exit(0)

recipe = os.environ["CHECK_MAKEFILE_RECIPE_CHECKMAKE"]

findings = []
for raw in sys.stdin:
    raw = raw.rstrip("\n")
    if not raw:
        continue
    parts = raw.split("\t", 2)
    if len(parts) != 3:
        continue
    path, lineno, context = parts
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    findings.append(
        emit_json_finding(
            rule_id="checkmake",
            status="warn",
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=(
                f"checkmake reports `{context}` for {path}. "
                "checkmake catches Make-idiom mistakes regex checks miss."
            ),
            recommended_changes=recipe,
        )
    )

print_envelope(emit_rule_envelope("checkmake", findings))
'

emit_envelope() {
  local status="$1" # "ok" | "missing"
  CHECK_MAKEFILE_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_MAKEFILE_RECIPE_CHECKMAKE="${RECIPE_CHECKMAKE}" \
    CHECK_MAKEFILE_STATUS="${status}" \
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

  if ! command -v checkmake >/dev/null 2>&1; then
    : | emit_envelope "missing"
    exit 0
  fi

  local target
  {
    for target in "$@"; do
      collect_findings "${target}"
    done
  } | emit_envelope "ok"
  # set -o pipefail propagates collect_findings' path-not-found return (64).
  exit 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
