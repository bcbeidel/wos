#!/usr/bin/env bash
#
# check_prose.sh — Tier-1 prose pre-checks for Claude Code SKILL.md
# files. Emits a JSON ARRAY of two envelopes (rule_id="prose-hedge",
# rule_id="absolute-path") per scripts/_common.py.
#
# prose-hedge:    whole-word hedge match (etc, maybe, probably, somehow,
#                 generally, sometimes, TBD) plus the literal `???`,
#                 outside fenced code blocks. WARN.
# absolute-path:  /home/..., /Users/..., ~/..., Windows drive-letter
#                 paths, multi-component backslash paths, outside fenced
#                 code blocks. WARN.
#
# Usage:
#   check_prose.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (WARN only — never produces FAIL)
#   1   one or more FAIL findings (not produced by this script)
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, find, basename, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename python3)
readonly HEDGES=(etc maybe probably somehow generally sometimes TBD)

readonly RECIPE_PROSE_HEDGE='Replace hedges (etc, maybe, probably, somehow, generally, sometimes, TBD, ???) with direct phrasing or delete the hedge. Hedges propagate ambiguity into model behavior — agents read "generally" as "feel free to skip this." Commit to the directive; if a real exception exists, name it explicitly.'

readonly RECIPE_ABSOLUTE_PATH='Convert absolute paths (/home/..., /Users/..., ~/..., C:\\..., backslash paths) to relative paths or environment variables. Absolute paths break the skill on relocation and embed the author'\''s machine layout. Use $HOME, ${PROJECT_ROOT}, or relative paths anchored to the skill or repo root.'

usage() {
  cat <<'EOF'
check_prose.sh — Prose pre-checks for Claude Code SKILL.md files.

Usage:
  check_prose.sh <path> [<path> ...]

Checks:
  prose-hedge       whole-word matches for etc, maybe, probably,
                    somehow, generally, sometimes, TBD, ??? outside
                    fenced code blocks (WARN)
  absolute-path     /home/..., /Users/..., ~/..., C:\... drive-letter
                    paths, or multi-component backslash paths outside
                    code (WARN)

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
    awk | find | basename) printf 'should be preinstalled on any POSIX system' ;;
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

# Emit findings as TSV: <rule_id>\t<file>\t<line>\t<context>
scan_hedges() {
  local file="$1"
  local hedge_list
  hedge_list="$(printf '%s|' "${HEDGES[@]}")"
  hedge_list="${hedge_list%|}"
  awk -v hedges="${hedge_list}" -v f="${file}" '
    BEGIN { IGNORECASE = 1; in_fence = 0 }
    {
      if ($0 ~ /^[[:space:]]*```/ || $0 ~ /^[[:space:]]*~~~/) {
        in_fence = !in_fence; next
      }
      if (in_fence) next
      line = $0
      gsub(/`[^`]*`/, "", line)
      if (index(line, "???") > 0) {
        printf "prose-hedge\t%s\t%d\thedge \"???\" at line %d\n", f, NR, NR
      }
      n = split(line, toks, /[^A-Za-z]+/)
      for (i = 1; i <= n; i++) {
        t = tolower(toks[i])
        if (t == "") continue
        split(hedges, hl, "|")
        for (j in hl) {
          if (t == tolower(hl[j])) {
            printf "prose-hedge\t%s\t%d\thedge \"%s\" at line %d\n", f, NR, hl[j], NR
            break
          }
        }
      }
    }
  ' "${file}"
}

scan_abs_paths() {
  local file="$1"
  awk -v f="${file}" '
    BEGIN { in_fence = 0 }
    {
      if ($0 ~ /^[[:space:]]*```/ || $0 ~ /^[[:space:]]*~~~/) {
        in_fence = !in_fence; next
      }
      if (in_fence) next
      line = $0
      gsub(/`[^`]*`/, "", line)
      if (match(line, /(^|[^A-Za-z0-9_])\/home\//) || match(line, /(^|[^A-Za-z0-9_])\/Users\//)) {
        printf "absolute-path\t%s\t%d\tPOSIX absolute path (/home/ or /Users/) at line %d\n", f, NR, NR
      }
      else if (match(line, /(^|[[:space:]])~\//)) {
        printf "absolute-path\t%s\t%d\ttilde home path (~/) at line %d\n", f, NR, NR
      }
      else if (match(line, /(^|[^A-Za-z0-9_])[A-Za-z]:\\/) || match(line, /(^|[^A-Za-z0-9_])[A-Za-z]:\//)) {
        printf "absolute-path\t%s\t%d\tWindows drive-letter path at line %d\n", f, NR, NR
      }
      else if (match(line, /[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+/)) {
        printf "absolute-path\t%s\t%d\tbackslash path (3+ components) at line %d\n", f, NR, NR
      }
    }
  ' "${file}"
}

scan_file() {
  local file="$1"
  scan_hedges "${file}"
  scan_abs_paths "${file}"
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    scan_file "${target}"
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      scan_file "${file}"
    done < <(
      find "${target}" -type f -name 'SKILL.md' \
        -not -path '*/_shared/*' \
        2>/dev/null
    )
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_SKILL_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipes = {
    "prose-hedge": os.environ["CHECK_SKILL_RECIPE_PROSE_HEDGE"],
    "absolute-path": os.environ["CHECK_SKILL_RECIPE_ABSOLUTE_PATH"],
}

per_rule = {"prose-hedge": [], "absolute-path": []}
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
            status="warn",
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=f"{path}: {context}.",
            recommended_changes=recipes[rule_id],
        )
    )

envelopes = [
    emit_rule_envelope(rule_id="prose-hedge", findings=per_rule["prose-hedge"]),
    emit_rule_envelope(rule_id="absolute-path", findings=per_rule["absolute-path"]),
]
print_envelope(envelopes)
if any(e["overall_status"] == "fail" for e in envelopes):
    sys.exit(1)
'

emit_envelopes() {
  CHECK_SKILL_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SKILL_RECIPE_PROSE_HEDGE="${RECIPE_PROSE_HEDGE}" \
    CHECK_SKILL_RECIPE_ABSOLUTE_PATH="${RECIPE_ABSOLUTE_PATH}" \
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
  local target
  local rc=0
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
