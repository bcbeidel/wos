#!/usr/bin/env bash
#
# check_frontmatter.sh — Deterministic Tier-1 frontmatter checks for
# Claude Code SKILL.md files. Emits a JSON ARRAY of four envelopes
# (rule_id="required-frontmatter", rule_id="version-shape",
# rule_id="description-cap", rule_id="license-presence") per
# scripts/_common.py.
#
# required-frontmatter (FAIL): `name`, `description`, `version`, `owner`
#                              present and non-empty.
# version-shape (FAIL):        `version` matches ^[0-9]+\.[0-9]+\.[0-9]+$.
# description-cap (FAIL):      `description` ≤ 1024 chars; combined
#                              with `when_to_use` ≤ 1536.
# license-presence (WARN):     advisory — `license` field absent.
#
# Name slug / reserved-token checks live in check_identity.sh.
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
#   awk, find, basename, head, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename head python3)
readonly REQUIRED_KEYS=(name description version owner)
readonly DESCRIPTION_CAP=1024
readonly COMBINED_CAP=1536

readonly RECIPE_REQUIRED_FRONTMATTER='Add the missing key(s) to the frontmatter — `name`, `description`, `version`, `owner` are all required and non-empty. These four fields anchor identity, routing, cache-busting, and ownership; missing any degrades discoverability or releases. A skill with no `owner` rots unclaimed.'

readonly RECIPE_VERSION_SHAPE='Rewrite `version` as semver MAJOR.MINOR.PATCH (three dot-separated integers). FROM `1.0` / `v1.0.0` / `0.1-beta`; TO `1.0.0`. Semver is the cache-busting signal consumers rely on; non-semver strings confuse release tooling and break version comparison.'

readonly RECIPE_DESCRIPTION_CAP='Split trigger phrases into `when_to_use` (combined cap 1536) rather than compressing the description. The description is the primary retrieval signal; compressing it erodes routing. Keep `description` ≤ 1024 (trigger opener + one-sentence purpose); enumerate triggers in `when_to_use`.'

readonly RECIPE_LICENSE_PRESENCE='Add `license:` to the frontmatter — an SPDX identifier (e.g., `MIT`) or a short reference to a bundled `LICENSE` file. Spec-optional per Agent Skills, but downstream reusers need redistribution terms before forking. Default to the host repo'\''s license unless the skill ships under different terms.'

usage() {
  cat <<'EOF'
check_frontmatter.sh — Frontmatter checks for Claude Code SKILL.md files.

Usage:
  check_frontmatter.sh <path> [<path> ...]

Checks:
  required-frontmatter  `name` / `description` / `version` / `owner`
                        present and non-empty (FAIL)
  version-shape         ^[0-9]+\.[0-9]+\.[0-9]+$ semver (FAIL)
  description-cap       `description` ≤ 1024; combined ≤ 1536 (FAIL)
  license-presence      `license` field present (WARN; toolkit-opinion)

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

# Read a scalar value (possibly a folded block scalar under `>` or `>-`)
# for a top-level frontmatter key. stdout: value; exit 0 = present.
read_value() {
  local file="$1" key="$2"
  awk -v k="${key}" '
    function strip_quotes(s) {
      if (match(s, /^".*"$/) || match(s, /^'"'"'.*'"'"'$/)) {
        return substr(s, 2, length(s) - 2)
      }
      return s
    }
    BEGIN { in_fm = 0; mode = "none"; acc = ""; found = 0 }
    NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
    in_fm && /^---[[:space:]]*$/ {
      if (found) { print acc }
      exit found ? 0 : 1
    }
    in_fm {
      if (mode == "block") {
        if ($0 ~ /^[A-Za-z_][A-Za-z0-9_-]*:/) {
          print acc
          exit 0
        }
        line = $0
        sub(/^[[:space:]]+/, "", line)
        if (line == "") {
          acc = acc " "
        } else {
          if (acc == "") { acc = line } else { acc = acc " " line }
        }
        next
      }
      pat = "^" k ":[[:space:]]*"
      if (match($0, pat)) {
        val = substr($0, RLENGTH + 1)
        sub(/[[:space:]]+$/, "", val)
        if (val == ">" || val == ">-" || val == "|" || val == "|-") {
          mode = "block"
          acc = ""
          found = 1
          next
        }
        print strip_quotes(val)
        found = 1
        exit 0
      }
    }
    END {
      if (mode == "block") {
        print acc
        exit 0
      }
      exit found ? 0 : 1
    }
  ' "${file}" 2>/dev/null
}

char_count() {
  printf '%s' "$1" | wc -c | tr -d ' '
}

# TSV: <rule_id>\t<status>\t<file>\t<line>\t<context>
emit_raw() {
  local file="$1"
  local first
  first="$(head -n 1 "${file}" 2>/dev/null || true)"
  if [[ "${first}" != "---" ]]; then
    printf 'required-frontmatter\tfail\t%s\t1\tfile does not begin with YAML frontmatter (---)\n' \
      "${file}"
    return 0
  fi

  local key val
  for key in "${REQUIRED_KEYS[@]}"; do
    if ! val="$(read_value "${file}" "${key}")"; then
      printf 'required-frontmatter\tfail\t%s\t1\tmissing required key '\''%s'\''\n' \
        "${file}" "${key}"
      continue
    fi
    val="${val%"${val##*[![:space:]]}"}"
    if [[ -z "${val}" ]]; then
      printf 'required-frontmatter\tfail\t%s\t1\tkey '\''%s'\'' is present but empty\n' \
        "${file}" "${key}"
    fi
  done

  if val="$(read_value "${file}" "version")"; then
    val="${val%"${val##*[![:space:]]}"}"
    if [[ -n "${val}" ]] && ! printf '%s' "${val}" | awk '
      { if ($0 ~ /^[0-9]+\.[0-9]+\.[0-9]+$/) exit 0; else exit 1 }
    '; then
      printf 'version-shape\tfail\t%s\t1\tversion '\''%s'\'' is not semver MAJOR.MINOR.PATCH\n' \
        "${file}" "${val}"
    fi
  fi

  local desc when desc_len when_len combined_len
  if desc="$(read_value "${file}" "description")"; then
    desc_len="$(char_count "${desc}")"
    if [[ "${desc_len}" -gt "${DESCRIPTION_CAP}" ]]; then
      printf 'description-cap\tfail\t%s\t1\tdescription is %s chars (cap %s)\n' \
        "${file}" "${desc_len}" "${DESCRIPTION_CAP}"
    fi
    if when="$(read_value "${file}" "when_to_use")"; then
      when_len="$(char_count "${when}")"
      combined_len=$((desc_len + when_len))
      if [[ "${combined_len}" -gt "${COMBINED_CAP}" ]]; then
        printf 'description-cap\tfail\t%s\t1\tdescription + when_to_use is %s chars (combined cap %s)\n' \
          "${file}" "${combined_len}" "${COMBINED_CAP}"
      fi
    fi
  fi

  if ! read_value "${file}" "license" >/dev/null 2>&1; then
    printf 'license-presence\twarn\t%s\t1\tfrontmatter has no '\''license'\'' key\n' \
      "${file}"
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
    "required-frontmatter": os.environ["CHECK_SKILL_RECIPE_REQUIRED_FRONTMATTER"],
    "version-shape": os.environ["CHECK_SKILL_RECIPE_VERSION_SHAPE"],
    "description-cap": os.environ["CHECK_SKILL_RECIPE_DESCRIPTION_CAP"],
    "license-presence": os.environ["CHECK_SKILL_RECIPE_LICENSE_PRESENCE"],
}
order = ["required-frontmatter", "version-shape", "description-cap", "license-presence"]

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
    CHECK_SKILL_RECIPE_REQUIRED_FRONTMATTER="${RECIPE_REQUIRED_FRONTMATTER}" \
    CHECK_SKILL_RECIPE_VERSION_SHAPE="${RECIPE_VERSION_SHAPE}" \
    CHECK_SKILL_RECIPE_DESCRIPTION_CAP="${RECIPE_DESCRIPTION_CAP}" \
    CHECK_SKILL_RECIPE_LICENSE_PRESENCE="${RECIPE_LICENSE_PRESENCE}" \
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
