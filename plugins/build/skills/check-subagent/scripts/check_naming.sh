#!/usr/bin/env bash
#
# check_naming.sh — Deterministic Tier-1 naming checks for subagent
# definitions. Emits a JSON ARRAY of three envelopes (rule_id="name-kebab",
# "name-stem-match", "generic-filename") per scripts/_common.py.
#
# Checks:
#   name-kebab        `name` matches ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ (WARN)
#   name-stem-match   filename stem equals `name` (FAIL)
#   generic-filename  filename is a generic placeholder (WARN; was HINT)
#
# Usage:
#   check_naming.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, basename, find, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk basename find python3)

readonly RECIPE_NAME_KEBAB='Convert `name` to kebab-case (lowercase + hyphens). If the filename follows the old casing, rename the file to match. Kebab-case is the cross-family consensus convention and matches Claude Code documented routing examples; mixed casing risks case-sensitivity mismatches across filesystems. FROM `name: TypeScriptLinter`; TO `name: typescript-linter`.'

readonly RECIPE_NAME_STEM_MATCH='Either rename the file so its stem matches `name`, or change `name` to match the stem. The filename is the first discovery signal; mismatches cause reviewer confusion and make directory scans unreliable. FROM file `ts-linter.md` + `name: typescript-linter`; TO file `typescript-linter.md` + `name: typescript-linter`.'

readonly RECIPE_GENERIC_FILENAME='Rename the file to describe the agent primary role (e.g., `typescript-linter.md`, `migration-reviewer.md`) rather than `agent.md` / `helper.md` / `subagent.md`. Generic stems are placeholders that survived past initial scaffolding; they degrade discovery and reviewer comprehension.'

usage() {
  cat <<'EOF'
check_naming.sh — Audit subagent name field and filename.

Usage:
  check_naming.sh <path> [<path> ...]

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
    awk | basename | find) printf 'should be preinstalled on any POSIX system' ;;
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

extract_name() {
  awk '
    /^---[[:space:]]*$/ {
      if (++count == 1) { inside = 1; next }
      if (count == 2)   { exit }
    }
    inside && /^name:[[:space:]]*/ {
      val = $0
      sub(/^name:[[:space:]]*/, "", val)
      if (val ~ /^".*"$/) { val = substr(val, 2, length(val) - 2) }
      else if (val ~ /^'\''.*'\''$/) { val = substr(val, 2, length(val) - 2) }
      print val
      exit
    }
  ' "$1"
}

is_generic_stem() {
  case "$1" in
    agent | agents | helper | default | subagent | test | example) return 0 ;;
  esac
  return 1
}

# TSV: <rule_id>\t<status>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  case "${file}" in
    *.md) ;;
    *) return ;;
  esac

  local stem
  stem="$(basename "${file}" .md)"

  if is_generic_stem "${stem}"; then
    printf 'generic-filename\twarn\t%s\t1\tfilename stem '\''%s'\'' is a generic placeholder\n' \
      "${file}" "${stem}"
  fi

  local name
  name="$(extract_name "${file}")"

  if [[ -n "${name}" ]]; then
    if ! printf '%s' "${name}" | awk '
      /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/ { exit 0 }
      { exit 1 }
    '; then
      printf 'name-kebab\twarn\t%s\t1\tname '\''%s'\'' is not kebab-case\n' \
        "${file}" "${name}"
    fi

    if [[ "${name}" != "${stem}" ]]; then
      printf 'name-stem-match\tfail\t%s\t1\tfilename stem '\''%s'\'' does not equal name '\''%s'\''\n' \
        "${file}" "${stem}" "${name}"
    fi
  fi
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
    "name-kebab": os.environ["CHECK_SUBAGENT_RECIPE_NAME_KEBAB"],
    "name-stem-match": os.environ["CHECK_SUBAGENT_RECIPE_NAME_STEM_MATCH"],
    "generic-filename": os.environ["CHECK_SUBAGENT_RECIPE_GENERIC_FILENAME"],
}
order = ["name-kebab", "name-stem-match", "generic-filename"]

per_rule = {r: [] for r in order}
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 4)
    if len(parts) != 5:
        continue
    rule_id, status, path, lineno, context = parts
    if rule_id not in per_rule:
        continue
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    per_rule[rule_id].append(
        emit_json_finding(
            rule_id=rule_id,
            status=status,
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
    CHECK_SUBAGENT_RECIPE_NAME_KEBAB="${RECIPE_NAME_KEBAB}" \
    CHECK_SUBAGENT_RECIPE_NAME_STEM_MATCH="${RECIPE_NAME_STEM_MATCH}" \
    CHECK_SUBAGENT_RECIPE_GENERIC_FILENAME="${RECIPE_GENERIC_FILENAME}" \
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
