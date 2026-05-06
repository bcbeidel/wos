#!/usr/bin/env bash
#
# check_identity.sh — Deterministic Tier-1 identity checks for Claude
# Code SKILL.md files. Emits a JSON ARRAY of five envelopes
# (rule_id="filename", rule_id="directory-basename",
# rule_id="name-slug", rule_id="reserved-names",
# rule_id="name-uniqueness") per scripts/_common.py.
#
# filename (FAIL):           file must be named exactly SKILL.md.
# directory-basename (FAIL): parent dir basename equals frontmatter
#                            `name`.
# name-slug (FAIL):          `name` matches ^[a-z0-9]+(-[a-z0-9]+)*$,
#                            ≤64 chars.
# reserved-names (FAIL):     `name` must not contain `anthropic` or
#                            `claude`.
# name-uniqueness (FAIL):    no two audited skills share the same
#                            `name`.
#
# Usage:
#   check_identity.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, find, basename, dirname, sort, uniq, paste, mktemp, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename dirname sort uniq paste mktemp python3)

readonly RECIPE_FILENAME='Rename the file to `SKILL.md` (case-sensitive). Claude Code'\''s skill loader matches the filename exactly; lowercase or extension variants are invisible to the loader. FROM `skill.md` / `Skill.md`; TO `SKILL.md`.'

readonly RECIPE_DIRECTORY_BASENAME='Either rename the directory to match the frontmatter `name`, or update `name` to match the directory. Prefer renaming the directory unless the skill is already published. The skill collection keys on `name` for routing — drift between directory and identifier breaks discovery.'

readonly RECIPE_NAME_SLUG='Rewrite `name` as lowercase kebab-case matching ^[a-z0-9]+(-[a-z0-9]+)*$ and ≤64 chars. FROM `CSV_to_Parquet` / `convert-csv-to-apache-parquet-with-very-long-name`; TO `csv-to-parquet`. Other forms break tooling that parses skill names as identifiers; over-long names degrade routing match quality. Move detail to `description`.'

readonly RECIPE_RESERVED_NAMES='Rename the skill without the reserved token (`anthropic` or `claude`). FROM `claude-helper`; TO `workflow-helper`. These tokens collide with platform-owned namespaces and are rejected at skill-load time.'

readonly RECIPE_NAME_UNIQUENESS='Rename one of the colliding skills to a distinct, more specific name (or merge if the workflows are genuinely identical). FROM two skills both named `deploy`; TO `deploy-staging` and `deploy-production`. Name collisions force arbitrary selection; routing becomes nondeterministic.'

usage() {
  cat <<'EOF'
check_identity.sh — Identity checks for Claude Code SKILL.md files.

Usage:
  check_identity.sh <path> [<path> ...]

Checks:
  filename            must be exactly SKILL.md (case-sensitive)
  directory-basename  parent dir basename == frontmatter `name`
  name-slug           ^[a-z0-9]+(-[a-z0-9]+)*$, ≤64 chars
  reserved-names      `name` must not contain `anthropic` or `claude`
  name-uniqueness     no two audited skills share the same `name`

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
    awk | find | basename | dirname | sort | uniq | paste | mktemp) printf 'should be preinstalled on any POSIX system' ;;
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

read_scalar() {
  local file="$1" key="$2"
  awk -v k="${key}" '
    BEGIN { in_fm = 0 }
    NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
    in_fm && /^---[[:space:]]*$/ { exit }
    in_fm {
      pat = "^" k ":[[:space:]]*"
      if (match($0, pat)) {
        val = substr($0, RLENGTH + 1)
        sub(/[[:space:]]+$/, "", val)
        if (match(val, /^".*"$/) || match(val, /^'"'"'.*'"'"'$/)) {
          val = substr(val, 2, length(val) - 2)
        }
        print val
        exit
      }
    }
  ' "${file}" 2>/dev/null || true
}

# TSV: <rule_id>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  local base dir_base name len
  base="$(basename "${file}")"
  if [[ "${base}" != "SKILL.md" ]]; then
    printf 'filename\t%s\t1\tfile is named '\''%s'\'' (expected '\''SKILL.md'\'')\n' \
      "${file}" "${base}"
  fi

  name="$(read_scalar "${file}" "name")"
  if [[ -z "${name}" ]]; then
    return 0
  fi

  dir_base="$(basename "$(dirname "${file}")")"
  if [[ "${dir_base}" != "${name}" ]]; then
    printf 'directory-basename\t%s\t1\tparent dir '\''%s'\'' does not match frontmatter name '\''%s'\''\n' \
      "${file}" "${dir_base}" "${name}"
  fi

  len=${#name}
  if [[ "${len}" -gt 64 ]]; then
    printf 'name-slug\t%s\t1\tname '\''%s'\'' is %s chars (cap 64)\n' \
      "${file}" "${name}" "${len}"
  fi
  if ! printf '%s' "${name}" | awk '
    { if ($0 ~ /^[a-z0-9]+(-[a-z0-9]+)*$/) exit 0; else exit 1 }
  '; then
    printf 'name-slug\t%s\t1\tname '\''%s'\'' is not lowercase kebab-case\n' \
      "${file}" "${name}"
  fi

  case "${name}" in
    *anthropic* | *claude*)
      printf 'reserved-names\t%s\t1\tname '\''%s'\'' contains a platform-reserved token\n' \
        "${file}" "${name}"
      ;;
  esac

  printf '%s\t%s\n' "${name}" "${file}" >>"${UNIQ_LOG}"
}

emit_uniqueness() {
  if [[ ! -s "${UNIQ_LOG}" ]]; then
    return 0
  fi
  local dup_names name file others
  dup_names="$(awk -F'\t' '{print $1}' "${UNIQ_LOG}" | sort | uniq -d)"
  if [[ -z "${dup_names}" ]]; then
    return 0
  fi
  while IFS= read -r name; do
    [[ -n "${name}" ]] || continue
    others="$(awk -F'\t' -v n="${name}" '$1 == n { print $2 }' "${UNIQ_LOG}" | paste -sd ',' -)"
    while IFS= read -r file; do
      printf 'name-uniqueness\t%s\t1\tname '\''%s'\'' collides with: %s\n' \
        "${file}" "${name}" "${others}"
    done < <(awk -F'\t' -v n="${name}" '$1 == n { print $2 }' "${UNIQ_LOG}")
  done <<<"${dup_names}"
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    emit_raw "${target}"
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      emit_raw "${file}"
    done < <(
      find "${target}" -type f \
        \( -name 'SKILL.md' -o -name 'Skill.md' -o -name 'skill.md' \) \
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
    "filename": os.environ["CHECK_SKILL_RECIPE_FILENAME"],
    "directory-basename": os.environ["CHECK_SKILL_RECIPE_DIRECTORY_BASENAME"],
    "name-slug": os.environ["CHECK_SKILL_RECIPE_NAME_SLUG"],
    "reserved-names": os.environ["CHECK_SKILL_RECIPE_RESERVED_NAMES"],
    "name-uniqueness": os.environ["CHECK_SKILL_RECIPE_NAME_UNIQUENESS"],
}
order = ["filename", "directory-basename", "name-slug", "reserved-names", "name-uniqueness"]

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
  CHECK_SKILL_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SKILL_RECIPE_FILENAME="${RECIPE_FILENAME}" \
    CHECK_SKILL_RECIPE_DIRECTORY_BASENAME="${RECIPE_DIRECTORY_BASENAME}" \
    CHECK_SKILL_RECIPE_NAME_SLUG="${RECIPE_NAME_SLUG}" \
    CHECK_SKILL_RECIPE_RESERVED_NAMES="${RECIPE_RESERVED_NAMES}" \
    CHECK_SKILL_RECIPE_NAME_UNIQUENESS="${RECIPE_NAME_UNIQUENESS}" \
    python3 -c "${EMIT_PY}"
}

UNIQ_LOG=""

cleanup() {
  [[ -n "${UNIQ_LOG}" ]] && [[ -f "${UNIQ_LOG}" ]] && rm -f "${UNIQ_LOG}"
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

  UNIQ_LOG="$(mktemp -t check_identity.XXXXXX)"
  trap cleanup EXIT INT TERM

  local target rc=0
  {
    for target in "$@"; do
      scan_path "${target}"
    done
    emit_uniqueness
  } | emit_envelopes || rc=$?
  exit "${rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
