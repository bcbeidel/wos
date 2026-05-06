#!/usr/bin/env bash
#
# check_tools.sh — Deterministic Tier-1 tool-allowlist checks for
# subagent definitions. Emits a JSON ARRAY of four envelopes
# (rule_id="tools-omitted", "tools-wildcard", "agent-listed",
# "parallel-write-risk") per scripts/_common.py.
#
# Checks:
#   tools-omitted        tools key absent — spec defaults to full grant (WARN)
#   tools-wildcard       tools contains *, all, or all_tools (FAIL)
#   agent-listed         Agent listed in tools for a subagent-scope file (WARN)
#   parallel-write-risk  background: true + Write/Edit without
#                        isolation: worktree (WARN)
#
# Usage:
#   check_tools.sh <path> [<path> ...]
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

readonly RECIPE_TOOLS_OMITTED='Add a `tools` list declaring the minimum set the workflow requires. Omitting `tools` grants the full tool set by default; explicit declaration is the primary least-privilege mechanism. If the workflow genuinely needs all tools, state the justification in a `## Rationale` section. FROM no `tools:`; TO `tools:\n  - Read\n  - Grep\n  - Glob`.'

readonly RECIPE_TOOLS_WILDCARD='Replace the wildcard with an enumerated list of the tools the workflow uses. Wildcards (`*`, `all`, `all_tools`) are equivalent to omitting `tools`: both grant the full set; enumeration is the only least-privilege surface. FROM `tools: ["*"]`; TO `tools: [Read, Grep, Glob]`.'

readonly RECIPE_AGENT_LISTED='Remove `Agent` from the `tools` list. The Agent tool is filtered at the platform level for subagents; listing it has no effect and misleads readers. (If the definition runs as main thread via `claude --agent <name>`, move it out of `.claude/agents/`.) FROM `tools: [Read, Agent]`; TO `tools: [Read]`.'

readonly RECIPE_PARALLEL_WRITE_RISK='Add `isolation: worktree` to the frontmatter, or drop `background: true` if parallelism is not actually needed. Parallel subagents writing shared files conflict without worktree isolation; `isolation: worktree` gives each subagent a clean working copy. FROM `tools: [Write]\nbackground: true`; TO `tools: [Write]\nbackground: true\nisolation: worktree`.'

usage() {
  cat <<'EOF'
check_tools.sh — Audit subagent tools allowlist hygiene.

Usage:
  check_tools.sh <path> [<path> ...]

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

extract_frontmatter() {
  awk '
    /^---[[:space:]]*$/ {
      if (++count == 1) { inside = 1; next }
      if (count == 2)   { exit }
    }
    inside { print }
  ' "$1"
}

tools_list() {
  printf '%s\n' "$1" | awk '
    /^tools:/ {
      if ($0 ~ /\[/) {
        line = $0
        sub(/^tools:[[:space:]]*\[/, "", line)
        sub(/\].*$/, "", line)
        n = split(line, items, /,/)
        for (i = 1; i <= n; i++) {
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", items[i])
          gsub(/^"|"$|^'\''|'\''$/, "", items[i])
          if (items[i] != "") print items[i]
        }
      } else {
        in_tools = 1
      }
      next
    }
    in_tools && /^[^ \t-]/ { in_tools = 0 }
    in_tools && /^[[:space:]]*-[[:space:]]/ {
      item = $0
      sub(/^[[:space:]]*-[[:space:]]*/, "", item)
      gsub(/^"|"$|^'\''|'\''$/, "", item)
      gsub(/[[:space:]]+$/, "", item)
      if (item != "") print item
    }
  '
}

has_key() {
  printf '%s\n' "$1" | awk -v k="$2" '
    $0 ~ "^" k ":" { found = 1 }
    END { exit (found ? 0 : 1) }
  '
}

get_scalar_value() {
  printf '%s\n' "$1" | awk -v k="$2" '
    $0 ~ "^" k ":[[:space:]]*" {
      val = $0
      sub("^" k ":[[:space:]]*", "", val)
      gsub(/^"|"$|^'\''|'\''$/, "", val)
      gsub(/[[:space:]]+$/, "", val)
      print val
      exit
    }
  '
}

# TSV: <rule_id>\t<status>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  case "${file}" in
    *.md) ;;
    *) return ;;
  esac

  local fm
  fm="$(extract_frontmatter "${file}")"
  [[ -z "${fm}" ]] && return

  if ! has_key "${fm}" "tools"; then
    printf 'tools-omitted\twarn\t%s\t1\ttools key absent — Claude Code grants the full tool set by default\n' \
      "${file}"
    return
  fi

  local tools
  tools="$(tools_list "${fm}")"

  local item
  while IFS= read -r item; do
    [[ -z "${item}" ]] && continue
    case "${item}" in
      '*' | all | all_tools | ALL)
        printf 'tools-wildcard\tfail\t%s\t1\ttools contains wildcard entry '\''%s'\''\n' \
          "${file}" "${item}"
        ;;
    esac
  done <<<"${tools}"

  while IFS= read -r item; do
    if [[ "${item}" = "Agent" ]]; then
      printf 'agent-listed\twarn\t%s\t1\tAgent listed in tools — filtered at platform level for subagents, no effect\n' \
        "${file}"
    fi
  done <<<"${tools}"

  local background isolation
  background="$(get_scalar_value "${fm}" "background")"
  isolation="$(get_scalar_value "${fm}" "isolation")"
  if [[ "${background}" = "true" ]]; then
    local has_write=0
    while IFS= read -r item; do
      case "${item}" in
        Write | Edit) has_write=1 ;;
      esac
    done <<<"${tools}"
    if [[ "${has_write}" -eq 1 ]] && [[ "${isolation}" != "worktree" ]]; then
      printf 'parallel-write-risk\twarn\t%s\t1\tbackground: true with Write/Edit granted but isolation: worktree absent\n' \
        "${file}"
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
    "tools-omitted": os.environ["CHECK_SUBAGENT_RECIPE_TOOLS_OMITTED"],
    "tools-wildcard": os.environ["CHECK_SUBAGENT_RECIPE_TOOLS_WILDCARD"],
    "agent-listed": os.environ["CHECK_SUBAGENT_RECIPE_AGENT_LISTED"],
    "parallel-write-risk": os.environ["CHECK_SUBAGENT_RECIPE_PARALLEL_WRITE_RISK"],
}
order = ["tools-omitted", "tools-wildcard", "agent-listed", "parallel-write-risk"]

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
    CHECK_SUBAGENT_RECIPE_TOOLS_OMITTED="${RECIPE_TOOLS_OMITTED}" \
    CHECK_SUBAGENT_RECIPE_TOOLS_WILDCARD="${RECIPE_TOOLS_WILDCARD}" \
    CHECK_SUBAGENT_RECIPE_AGENT_LISTED="${RECIPE_AGENT_LISTED}" \
    CHECK_SUBAGENT_RECIPE_PARALLEL_WRITE_RISK="${RECIPE_PARALLEL_WRITE_RISK}" \
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
