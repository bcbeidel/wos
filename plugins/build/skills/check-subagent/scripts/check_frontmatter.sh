#!/usr/bin/env bash
#
# check_frontmatter.sh — Deterministic Tier-1 frontmatter checks for
# Claude Code subagent definitions. Emits a JSON ARRAY of six envelopes
# (rule_id="fm-delimiter", "fm-name", "fm-description",
# "fm-description-length", "plugin-noop", "memory-expansion") per
# scripts/_common.py.
#
# Checks:
#   fm-delimiter            file begins with a ---...--- YAML block (FAIL)
#   fm-name                 `name` key present and non-empty (FAIL)
#   fm-description          `description` key present and non-empty (FAIL)
#   fm-description-length   `description` <=1,024 characters (FAIL)
#   plugin-noop             plugin-scoped files do not set
#                           permissionMode/hooks/mcpServers (WARN)
#   memory-expansion        memory: set alongside narrow tools omitting
#                           Read/Write/Edit (WARN)
#
# Usage:
#   check_frontmatter.sh <path> [<path> ...]
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

readonly RECIPE_FM_DELIMITER='Add a `---`-delimited YAML block as the first lines of the file. Frontmatter is the machine-parseable metadata surface Claude Code reads to register the subagent — without it, the file is ignored. Minimum: `name`, `description`, `tools`. FROM bare `# My Agent` start; TO `---\nname: my-agent\ndescription: ...\ntools:\n  - Read\n---`.'

readonly RECIPE_FM_NAME='Add a `name` field matching the filename stem. `name` is the agent identifier the routing agent addresses when delegating; missing or empty values make the subagent unroutable. FROM `description: ...` only; TO `name: linter\ndescription: ...`.'

readonly RECIPE_FM_DESCRIPTION='Add a routing-rule description: verb-phrase capability + trigger conditions + at least one exclusion + returned output. The description is the router classification prompt — empty means Claude has no basis to delegate. FROM no `description:`; TO `description: Lints staged TypeScript. Use after editing .ts/.tsx. Not for .js. Returns JSON.`.'

readonly RECIPE_FM_DESCRIPTION_LENGTH='Shorten the description to <=1,024 characters. Move overflow detail into body sections (`## When to invoke`, `## Scope`). Claude Code silently truncates over 1,024 chars without warning, stripping trailing exclusions or triggers and changing routing behavior. FROM 1,500-char inline workflow detail; TO 400-char routing contract + body.'

readonly RECIPE_PLUGIN_NOOP='Remove the field. For plugin-scoped subagents, the runtime silently strips `permissionMode`, `hooks`, and `mcpServers` at load time (security-scoped plugin restriction); leaving them implies behavior the runtime will not produce. FROM `permissionMode: acceptEdits` in plugin frontmatter; TO field removed.'

readonly RECIPE_MEMORY_EXPANSION='Either remove `memory:` (if memory is not genuinely needed), or expand the `tools` allowlist to include Read, Write, and Edit to match runtime behavior. When `memory:` is set, the runtime auto-enables those tools so the subagent can manage its memory files; a narrower list misleads readers about the agent capability surface. FROM `tools: [Grep]` + `memory: project`; TO `tools: [Grep, Read, Write, Edit]` + `memory: project`.'

usage() {
  cat <<'EOF'
check_frontmatter.sh — Audit subagent frontmatter shape.

Usage:
  check_frontmatter.sh <path> [<path> ...]

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

get_scalar() {
  local fm="$1"
  local key="$2"
  printf '%s\n' "${fm}" | awk -v k="${key}" '
    BEGIN { val = ""; folded = 0; literal = 0 }
    (folded || literal) && /^[^ \t]/ { folded = 0; literal = 0 }
    (folded || literal) && /^[[:space:]]+/ {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      if (val == "") { val = line } else { val = val (folded ? " " : "\n") line }
      next
    }
    $0 ~ "^" k ":[[:space:]]*" {
      rest = $0
      sub("^" k ":[[:space:]]*", "", rest)
      if (rest == ">" || rest == ">-") { folded = 1; next }
      if (rest == "|" || rest == "|-") { literal = 1; next }
      if (rest ~ /^".*"$/) { rest = substr(rest, 2, length(rest) - 2) }
      else if (rest ~ /^'\''.*'\''$/) { rest = substr(rest, 2, length(rest) - 2) }
      val = rest
    }
    END { print val }
  '
}

has_key() {
  local fm="$1"
  local key="$2"
  printf '%s\n' "${fm}" | awk -v k="${key}" '
    $0 ~ "^" k ":" { found = 1 }
    END { exit (found ? 0 : 1) }
  '
}

tools_contains() {
  local fm="$1"
  local needle="$2"
  printf '%s\n' "${fm}" | awk -v needle="${needle}" '
    BEGIN { in_tools = 0; hit = 0 }
    /^tools:/ {
      if ($0 ~ /\[/) {
        line = $0
        sub(/^tools:[[:space:]]*\[/, "", line)
        sub(/\].*$/, "", line)
        n = split(line, items, /,/)
        for (i = 1; i <= n; i++) {
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", items[i])
          gsub(/^"|"$|^'\''|'\''$/, "", items[i])
          if (items[i] == needle) { hit = 1 }
        }
        in_tools = 0
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
      if (item == needle) { hit = 1 }
    }
    END { exit (hit ? 0 : 1) }
  '
}

is_plugin_path() {
  case "$1" in
    *plugins/*/agents/*) return 0 ;;
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

  local fm
  fm="$(extract_frontmatter "${file}")"

  if [[ -z "${fm}" ]]; then
    printf 'fm-delimiter\tfail\t%s\t1\tno ---delimited YAML frontmatter block at file head\n' "${file}"
    return
  fi

  local name description
  name="$(get_scalar "${fm}" "name")"
  description="$(get_scalar "${fm}" "description")"

  if [[ -z "${name}" ]]; then
    printf 'fm-name\tfail\t%s\t1\tname key missing or empty\n' "${file}"
  fi

  if [[ -z "${description}" ]]; then
    printf 'fm-description\tfail\t%s\t1\tdescription key missing or empty\n' "${file}"
  else
    local dlen="${#description}"
    if [[ "${dlen}" -gt 1024 ]]; then
      printf 'fm-description-length\tfail\t%s\t1\tdescription is %s characters (>1024 — Claude Code silently truncates)\n' \
        "${file}" "${dlen}"
    fi
  fi

  if is_plugin_path "${file}"; then
    local noop_key
    for noop_key in permissionMode hooks mcpServers; do
      if has_key "${fm}" "${noop_key}"; then
        printf 'plugin-noop\twarn\t%s\t1\t%s set in plugin-scoped definition — silently ignored at load\n' \
          "${file}" "${noop_key}"
      fi
    done
  fi

  if has_key "${fm}" "memory" && has_key "${fm}" "tools"; then
    local missing=()
    local t
    for t in Read Write Edit; do
      if ! tools_contains "${fm}" "${t}"; then
        missing+=("${t}")
      fi
    done
    if [[ "${#missing[@]}" -gt 0 ]]; then
      printf 'memory-expansion\twarn\t%s\t1\tmemory: enabled — runtime auto-grants Read/Write/Edit; tools list is missing: %s\n' \
        "${file}" "${missing[*]}"
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
    "fm-delimiter": os.environ["CHECK_SUBAGENT_RECIPE_FM_DELIMITER"],
    "fm-name": os.environ["CHECK_SUBAGENT_RECIPE_FM_NAME"],
    "fm-description": os.environ["CHECK_SUBAGENT_RECIPE_FM_DESCRIPTION"],
    "fm-description-length": os.environ["CHECK_SUBAGENT_RECIPE_FM_DESCRIPTION_LENGTH"],
    "plugin-noop": os.environ["CHECK_SUBAGENT_RECIPE_PLUGIN_NOOP"],
    "memory-expansion": os.environ["CHECK_SUBAGENT_RECIPE_MEMORY_EXPANSION"],
}
order = ["fm-delimiter", "fm-name", "fm-description",
         "fm-description-length", "plugin-noop", "memory-expansion"]

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
    CHECK_SUBAGENT_RECIPE_FM_DELIMITER="${RECIPE_FM_DELIMITER}" \
    CHECK_SUBAGENT_RECIPE_FM_NAME="${RECIPE_FM_NAME}" \
    CHECK_SUBAGENT_RECIPE_FM_DESCRIPTION="${RECIPE_FM_DESCRIPTION}" \
    CHECK_SUBAGENT_RECIPE_FM_DESCRIPTION_LENGTH="${RECIPE_FM_DESCRIPTION_LENGTH}" \
    CHECK_SUBAGENT_RECIPE_PLUGIN_NOOP="${RECIPE_PLUGIN_NOOP}" \
    CHECK_SUBAGENT_RECIPE_MEMORY_EXPANSION="${RECIPE_MEMORY_EXPANSION}" \
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
