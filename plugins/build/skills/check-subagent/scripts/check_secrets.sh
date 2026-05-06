#!/usr/bin/env bash
#
# check_secrets.sh — Scan subagent definitions for committed secrets.
# Emits a JSON ARRAY containing a single envelope (rule_id="secret") per
# scripts/_common.py.
#
# Deterministic Tier-1 Safety check invoked by /build:check-subagent.
# Scans .md files under agents/ directories for well-known API key
# patterns and credential-shaped variable assignments, skipping obvious
# placeholders. Any match is FAIL — committed credentials leak via git
# history regardless of how they surface.
#
# Usage:
#   check_secrets.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing required dependency
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

readonly RECIPE_SECRET='Remove the secret from source. Document the credential requirement in the body and surface it via the invocation environment. FROM `API_KEY=sk-proj-abc123...` inline; TO body text "the operator sets UPSTREAM_API_KEY before invocation; the agent does not handle the secret directly." Rotation is mandatory — git history retains the exposed value, and a subagent treating a key as instruction is a prompt-injection surface.'

readonly PATTERN_NAMES=(
  "AWS access key"
  "GitHub personal access token"
  "GitHub fine-grained PAT"
  "OpenAI API key"
  "Anthropic API key"
  "Stripe live key"
  "PEM private key header"
)
readonly PATTERN_REGEXES=(
  'AKIA[0-9A-Z]{16}'
  'ghp_[A-Za-z0-9]{36}'
  'github_pat_[A-Za-z0-9_]{82}'
  'sk-[A-Za-z0-9]{48}'
  'sk-ant-[A-Za-z0-9_-]{80,}'
  'sk_live_[A-Za-z0-9]{24}'
  '-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'
)

GENERIC_VAR_REGEX="(password|secret|token|api_key|access_key"
GENERIC_VAR_REGEX+="|private_key)[[:space:]]*[:=][[:space:]]*"
GENERIC_VAR_REGEX+="[\"'][^\"']+[\"']"
readonly GENERIC_VAR_REGEX

usage() {
  cat <<'EOF'
check_secrets.sh — Scan subagent definitions for committed secrets.

Usage:
  check_secrets.sh <path> [<path> ...]

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

# TSV: <file>\t<line>\t<context>
scan_file() {
  local file="$1"
  local i name pattern hit line

  i=0
  while [[ "${i}" -lt "${#PATTERN_REGEXES[@]}" ]]; do
    name="${PATTERN_NAMES[${i}]}"
    pattern="${PATTERN_REGEXES[${i}]}"
    while IFS= read -r hit; do
      [[ -z "${hit}" ]] && continue
      line="${hit%%:*}"
      printf '%s\t%s\t%s pattern matched\n' "${file}" "${line}" "${name}"
    done < <(grep -nE "${pattern}" "${file}" 2>/dev/null || true)
    i=$((i + 1))
  done

  local placeholder_re="[:=][[:space:]]*[\"']"
  placeholder_re+="(your[-_]|example|redacted|null|none|undefined|"
  placeholder_re+="placeholder|todo|fixme|xxx|changeme|change[-_]me|"
  placeholder_re+="foo|bar|baz|abc|xyz)"

  while IFS= read -r hit; do
    [[ -z "${hit}" ]] && continue
    line="${hit%%:*}"
    printf '%s\t%s\tcredential-shaped variable assignment\n' "${file}" "${line}"
  done < <(
    grep -niE "${GENERIC_VAR_REGEX}" "${file}" 2>/dev/null \
      | grep -Ev "[:=][[:space:]]*[\"']\\\$" \
      | grep -Ev "[:=][[:space:]]*[\"']\\{" \
      | grep -Ev "[:=][[:space:]]*[\"']<" \
      | grep -iEv "${placeholder_re}" \
      || true
  )
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    case "${target}" in
      *.md) scan_file "${target}" ;;
    esac
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      scan_file "${file}"
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

recipe = os.environ["CHECK_SUBAGENT_RECIPE_SECRET"]

findings = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 2)
    if len(parts) != 3:
        continue
    path, lineno, context = parts
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    findings.append(
        emit_json_finding(
            rule_id="secret",
            status="fail",
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=(
                f"{path} line {line_int}: {context}. Subagent files are "
                "loaded automatically by Claude Code; a committed secret "
                "leaks via git history and surfaces as instruction "
                "content the model may treat as authoritative."
            ),
            recommended_changes=recipe,
        )
    )

envelope = emit_rule_envelope(rule_id="secret", findings=findings)
print_envelope([envelope])
if envelope["overall_status"] == "fail":
    sys.exit(1)
'

emit_envelopes() {
  CHECK_SUBAGENT_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SUBAGENT_RECIPE_SECRET="${RECIPE_SECRET}" \
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
