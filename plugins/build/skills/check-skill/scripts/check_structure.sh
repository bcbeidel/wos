#!/usr/bin/env bash
#
# check_structure.sh — Deterministic Tier-1 structure checks for
# Claude Code SKILL.md files. Emits a JSON ARRAY of three envelopes
# (rule_id="required-sections", rule_id="steps-shape",
# rule_id="examples-content") per scripts/_common.py.
#
# required-sections (FAIL):  `## When to use`, `## Prerequisites`,
#                            `## Steps`, `## Failure modes`,
#                            `## Examples` all present.
# steps-shape:               `## Steps` is a Markdown ordered list
#                            starting at 1. FAIL when not ordered or
#                            doesn't start at 1; WARN on non-sequential
#                            increments.
# examples-content (WARN):   `## Examples` contains at least one fenced
#                            code block.
#
# Usage:
#   check_structure.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, find, basename, head, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename head python3)
readonly REQUIRED_SECTIONS=("When to use" "Prerequisites" "Steps" "Failure modes" "Examples")

readonly RECIPE_REQUIRED_SECTIONS='Add the missing H2 section(s) — `## When to use`, `## Prerequisites`, `## Steps`, `## Failure modes`, `## Examples` — with real content (not placeholder headings). Silence on any of the five canonical sections is the structural anti-pattern: agents invent behavior where the skill is silent.'

readonly RECIPE_STEPS_SHAPE='Write `## Steps` as a Markdown ordered list starting at 1, one atomic action per item, sequential 1..N increments. FROM prose ("First read X, then validate Y"); TO `1. Read $ARGUMENTS. 2. Validate the input. 3. Write the output.` Numbered ordered lists are followed more reliably than prose or bullets — the structure itself is instruction.'

readonly RECIPE_EXAMPLES_CONTENT='Add at least one fenced code block (```) under `## Examples` showing the input, output, and any side effects. Concrete examples anchor the model better than abstract rules — models copy-paste better than they translate prose.'

usage() {
  cat <<'EOF'
check_structure.sh — Structure checks for Claude Code SKILL.md files.

Usage:
  check_structure.sh <path> [<path> ...]

Checks:
  required-sections  `## When to use` / `## Prerequisites` / `## Steps`
                     / `## Failure modes` / `## Examples` all present (FAIL)
  steps-shape        Markdown ordered list starting at 1; FAIL on
                     non-ordered or wrong start; WARN on gaps
  examples-content   at least one fenced code block (WARN)

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
    awk | find | basename | head) printf 'should be preinstalled on any POSIX system' ;;
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

# Strip frontmatter; print body lines only.
body_lines() {
  awk '
    BEGIN { in_fm = 0; past_fm = 0 }
    NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
    in_fm && /^---[[:space:]]*$/ { in_fm = 0; past_fm = 1; next }
    in_fm { next }
    !in_fm && !past_fm { past_fm = 1 }
    { print }
  ' "$1"
}

# Emits TSV: <rule_id>\t<status>\t<file>\t<line>\t<context>
check_required_sections() {
  local file="$1"
  local body missing="" section
  body="$(body_lines "${file}")"
  for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! printf '%s\n' "${body}" | awk -v s="${section}" '
      BEGIN { pat = "^## " s "[[:space:]]*$" }
      $0 ~ pat { found = 1; exit 0 }
      END { exit found ? 0 : 1 }
    '; then
      if [[ -n "${missing}" ]]; then
        missing="${missing}, ## ${section}"
      else
        missing="## ${section}"
      fi
    fi
  done
  if [[ -n "${missing}" ]]; then
    printf 'required-sections\tfail\t%s\t1\tmissing section(s): %s\n' \
      "${file}" "${missing}"
  fi
}

check_steps_shape() {
  local file="$1"
  local section
  section="$(awk '
    BEGIN { in_sec = 0 }
    /^## / {
      if (in_sec) { exit }
      if ($0 ~ /^## Steps[[:space:]]*$/) { in_sec = 1; next }
    }
    in_sec { print }
  ' "${file}" 2>/dev/null)"

  if [[ -z "${section}" ]]; then
    return 0
  fi

  local first_list_line
  first_list_line="$(printf '%s\n' "${section}" | awk '
    /^[[:space:]]*[-*+][[:space:]]+/ { print "UL:" $0; exit }
    /^[0-9]+\.[[:space:]]+/ { print "OL:" $0; exit }
  ')"

  if [[ -z "${first_list_line}" ]]; then
    printf 'steps-shape\tfail\t%s\t1\t## Steps contains no Markdown list\n' "${file}"
    return 0
  fi

  case "${first_list_line}" in
    UL:*)
      printf 'steps-shape\tfail\t%s\t1\t## Steps begins with an unordered list (expected ordered)\n' "${file}"
      return 0
      ;;
  esac

  local nums first_num
  nums="$(printf '%s\n' "${section}" | awk '
    /^[0-9]+\.[[:space:]]+/ {
      match($0, /^[0-9]+/)
      print substr($0, RSTART, RLENGTH)
    }
  ')"
  first_num="$(printf '%s\n' "${nums}" | head -n 1)"
  if [[ "${first_num}" != "1" ]]; then
    printf 'steps-shape\tfail\t%s\t1\t## Steps ordered list starts at %s (expected 1)\n' \
      "${file}" "${first_num}"
    return 0
  fi
  local expect=1 n non_seq=""
  while IFS= read -r n; do
    [[ -z "${n}" ]] && continue
    if [[ "${n}" != "${expect}" ]]; then
      non_seq="${non_seq}${non_seq:+, }${n}"
    fi
    expect=$((n + 1))
  done <<<"${nums}"
  if [[ -n "${non_seq}" ]]; then
    printf 'steps-shape\twarn\t%s\t1\t## Steps ordered list has non-sequential numbering (unexpected: %s)\n' \
      "${file}" "${non_seq}"
  fi
}

check_examples_fenced() {
  local file="$1"
  local section
  section="$(awk '
    BEGIN { in_sec = 0 }
    /^## / {
      if (in_sec) { exit }
      if ($0 ~ /^## Examples[[:space:]]*$/) { in_sec = 1; next }
    }
    in_sec { print }
  ' "${file}" 2>/dev/null)"

  if [[ -z "${section}" ]]; then
    return 0
  fi

  if printf '%s\n' "${section}" | awk '
    /^[[:space:]]*```/ { found = 1; exit }
    /^[[:space:]]*~~~/ { found = 1; exit }
    END { exit found ? 0 : 1 }
  '; then
    return 0
  fi

  printf 'examples-content\twarn\t%s\t1\t## Examples contains no fenced code block\n' "${file}"
}

scan_file() {
  local file="$1"
  local first
  first="$(head -n 1 "${file}" 2>/dev/null || true)"
  # If no frontmatter, the body checks still run against whole file —
  # required-sections will likely flag everything. That's the point.
  : "${first}"
  check_required_sections "${file}"
  check_steps_shape "${file}"
  check_examples_fenced "${file}"
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
    "required-sections": os.environ["CHECK_SKILL_RECIPE_REQUIRED_SECTIONS"],
    "steps-shape": os.environ["CHECK_SKILL_RECIPE_STEPS_SHAPE"],
    "examples-content": os.environ["CHECK_SKILL_RECIPE_EXAMPLES_CONTENT"],
}
order = ["required-sections", "steps-shape", "examples-content"]

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
  CHECK_SKILL_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SKILL_RECIPE_REQUIRED_SECTIONS="${RECIPE_REQUIRED_SECTIONS}" \
    CHECK_SKILL_RECIPE_STEPS_SHAPE="${RECIPE_STEPS_SHAPE}" \
    CHECK_SKILL_RECIPE_EXAMPLES_CONTENT="${RECIPE_EXAMPLES_CONTENT}" \
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
