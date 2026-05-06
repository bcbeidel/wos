#!/usr/bin/env bash
#
# check_secrets.sh — Scan Python scripts for committed secrets. Emits a
# JSON ARRAY containing one envelope (rule_id="secret") per
# scripts/_common.py.
#
# secret (FAIL): committed API key / token / credential-shaped variable
# assignment.
#
# Usage:
#   check_secrets.sh <path> [<path> ...]
#
# Paths may be .py files or directories (top-level .py only).
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   grep, find, basename, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(grep find basename python3)

readonly _RULE_ORDER="secret"

readonly RECIPE_SECRET='Remove the secret from source. Replace with `os.environ.get("<VAR_NAME>")` and document the env var in the module docstring. Rotate any leaked credential — committed secrets leak through git history, logs, and backups. Externalizing to the environment is the minimum bar; a secret manager is better where available.

Example:
    import os
    API_KEY = os.environ.get("OPENAI_API_KEY")
    if not API_KEY:
        sys.exit("OPENAI_API_KEY not set")
'

usage() {
  cat <<'EOF'
check_secrets.sh — Scan Python scripts for committed secrets.

Usage:
  check_secrets.sh <path> [<path> ...]

Arguments:
  <path>   A .py file or directory to scan (top-level .py only).

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no findings
  1   one or more FAIL findings
  64  usage error
  69  missing dependency
EOF
}

install_hint() {
  case "${1}" in
    grep | find | basename) printf 'should be preinstalled on any POSIX system' ;;
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

# Parallel arrays: specific API key patterns and their display names.
# bash 3.2 has no associative arrays — use ordered arrays.
readonly PATTERN_NAMES=(
  "AWS access key"
  "GitHub personal access token"
  "GitHub fine-grained PAT"
  "OpenAI API key"
  "Anthropic API key"
  "Stripe live key"
)
readonly PATTERN_REGEXES=(
  'AKIA[0-9A-Z]{16}'
  'ghp_[A-Za-z0-9]{36}'
  'github_pat_[A-Za-z0-9_]{82}'
  'sk-[A-Za-z0-9]{48}'
  'sk-ant-[A-Za-z0-9_-]{80,}'
  'sk_live_[A-Za-z0-9]{24}'
)

# Credential-shaped variable assignment with a non-empty quoted value.
readonly GENERIC_VAR_REGEX="(password|secret|token|api_key|access_key|private_key)""\
[[:space:]]*=[[:space:]]*[\"'][^\"']+[\"']"

# TSV: <rule_id>\t<status>\t<file>\t<line>\t<context>
scan_file() {
  local file="$1"
  local i name pattern hit line

  i=0
  while [[ "${i}" -lt "${#PATTERN_REGEXES[@]}" ]]; do
    name="${PATTERN_NAMES[${i}]}"
    pattern="${PATTERN_REGEXES[${i}]}"
    while IFS= read -r hit; do
      line="${hit%%:*}"
      printf 'secret\tfail\t%s\t%s\t%s detected\n' "${file}" "${line}" "${name}"
    done < <(grep -nE "${pattern}" "${file}" 2>/dev/null || true)
    i=$((i + 1))
  done

  while IFS= read -r hit; do
    line="${hit%%:*}"
    printf 'secret\tfail\t%s\t%s\tcredential variable assignment\n' "${file}" "${line}"
  done < <(
    grep -niE "${GENERIC_VAR_REGEX}" "${file}" 2>/dev/null \
      | grep -Ev "=[[:space:]]*[\"']\\\$" \
      | grep -Ev "=[[:space:]]*[\"']\\{" \
      | grep -Ev "=[[:space:]]*[\"']<" \
      | grep -iEv "=[[:space:]]*[\"'](your[-_]|example|redacted|null|none|undefined|""\
placeholder|todo|fixme|xxx|changeme|change[-_]me|foo|bar|baz|abc|xyz)" \
      || true
  )
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    case "${target}" in
      *.py) scan_file "${target}" ;;
    esac
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      scan_file "${file}"
    done < <(find "${target}" -maxdepth 1 -type f -name '*.py' 2>/dev/null)
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_PY_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

order = os.environ["CHECK_PY_RULE_ORDER"].split(",")
recipes = {
    "secret": os.environ["CHECK_PY_RECIPE_SECRET"],
}

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
  CHECK_PY_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_PY_RULE_ORDER="${_RULE_ORDER}" \
    CHECK_PY_RECIPE_SECRET="${RECIPE_SECRET}" \
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
