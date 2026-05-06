#!/usr/bin/env bash
#
# check_location.sh — Deterministic Tier-1 location + extension check
# for Claude Code subagent definitions. Emits a JSON ARRAY of two
# envelopes (rule_id="location-dir", rule_id="location-ext") per
# scripts/_common.py.
#
# Subagents must live under an agents/ directory (.claude/agents/,
# ~/.claude/agents/, or plugins/<plugin>/agents/) with a .md extension.
# Files outside these paths are invisible to the Claude Code router.
#
# Usage:
#   check_location.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   basename, find, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(basename find python3)

readonly RECIPE_LOCATION_DIR='Move the file to `.claude/agents/` (project), `~/.claude/agents/` (user), or `plugins/<plugin>/agents/` (plugin scope). Claude Code only discovers subagent definitions under `agents/` directories; files elsewhere are invisible to the router regardless of content. FROM `.claude/helpers/my-agent.md`; TO `.claude/agents/my-agent.md`.'

readonly RECIPE_LOCATION_EXT='Rename the file to use a `.md` extension. Claude Code loads `.md` files only; other extensions are skipped at discovery. FROM `.claude/agents/my-agent.txt`; TO `.claude/agents/my-agent.md`.'

usage() {
  cat <<'EOF'
check_location.sh — Flag subagent files outside agents/ directories or with wrong extension.

Usage:
  check_location.sh <path> [<path> ...]

Arguments:
  <path>   A .md file or directory to scan (top-level files only).

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
    basename | find) printf 'should be preinstalled on any POSIX system' ;;
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

# TSV: <rule_id>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"

  case "${file}" in
    *.md) ;;
    *)
      printf 'location-ext\t%s\t1\textension is not .md\n' "${file}"
      ;;
  esac

  case "${file}" in
    */.claude/agents/* | */agents/* | .claude/agents/* | agents/*) ;;
    *)
      printf 'location-dir\t%s\t1\tfile is not under an agents/ directory\n' "${file}"
      ;;
  esac
}

scan_path() {
  local target="$1"
  local file

  if [[ -f "${target}" ]]; then
    emit_raw "${target}"
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      emit_raw "${file}"
    done < <(find "${target}" -maxdepth 1 -type f -name '*.md' 2>/dev/null)
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_SUBAGENT_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipes = {
    "location-dir": os.environ["CHECK_SUBAGENT_RECIPE_LOCATION_DIR"],
    "location-ext": os.environ["CHECK_SUBAGENT_RECIPE_LOCATION_EXT"],
}
order = ["location-dir", "location-ext"]

per_rule = {r: [] for r in order}
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 3)
    if len(parts) != 4:
        continue
    rule_id, path, lineno, context = parts
    if rule_id not in per_rule:
        continue
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    per_rule[rule_id].append(
        emit_json_finding(
            rule_id=rule_id,
            status="fail",
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=f"{path}: {context}.",
            recommended_changes=recipes[rule_id],
        )
    )

envelopes = [emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in order]
print_envelope(envelopes)
if any(e["overall_status"] == "fail" for e in envelopes):
    sys.exit(1)
'

emit_envelopes() {
  CHECK_SUBAGENT_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SUBAGENT_RECIPE_LOCATION_DIR="${RECIPE_LOCATION_DIR}" \
    CHECK_SUBAGENT_RECIPE_LOCATION_EXT="${RECIPE_LOCATION_EXT}" \
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
  local target rc=0
  {
    for target in "$@"; do
      scan_path "${target}"
    done
  } | emit_envelopes || rc=$?
  exit "${rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
