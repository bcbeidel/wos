#!/usr/bin/env bash
#
# check_secret.sh — Tier-1 secret scan for Claude Code SKILL.md files.
# Emits a JSON ARRAY containing a single envelope (rule_id="secret")
# per scripts/_common.py.
#
# Prefers `gitleaks detect --no-git --source <file>` when available;
# falls back to a built-in regex set (AWS / GitHub / OpenAI / Anthropic
# / Stripe keys, credential-shaped variable assignments) when gitleaks
# is absent. Any match is FAIL — committed credentials leak via git
# history regardless of how they surface.
#
# Usage:
#   check_secret.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, find, basename, grep, python3
#   (optional) gitleaks — used when present

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename grep python3)

readonly RECIPE_SECRET='Rotate the exposed credential immediately (assume the value in source is already compromised), then replace the literal with an environment-variable reference or vault path. Skill files are committed config; a committed credential is a breach regardless of where it surfaces. FROM `AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE`; TO `AWS_ACCESS_KEY=${AWS_ACCESS_KEY}`. Rotation is mandatory — git history retains the exposed value.'

usage() {
  cat <<'EOF'
check_secret.sh — Secret scan for Claude Code SKILL.md files.

Usage:
  check_secret.sh <path> [<path> ...]

Detection:
  Prefers `gitleaks detect --no-git --source <file>` when available.
  Falls back to built-in regex: AWS access keys, GitHub PATs, OpenAI /
  Anthropic / Stripe keys, credential-shaped variable assignments.

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings
  1   one or more FAIL findings
  64  usage error
  69  missing dependency

Installation (optional):
  brew install gitleaks         # macOS
  apt install gitleaks          # Debian/Ubuntu
EOF
}

install_hint() {
  case "${1}" in
    awk | find | basename | grep) printf 'should be preinstalled on any POSIX system' ;;
    python3) printf 'install Python 3.9+' ;;
    gitleaks) printf 'brew install gitleaks (or see https://github.com/gitleaks/gitleaks)' ;;
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
scan_with_gitleaks() {
  local file="$1"
  local output
  output="$(gitleaks detect --no-git --no-banner --source "${file}" --report-format json 2>/dev/null || true)"
  if [[ -z "${output}" ]] || [[ "${output}" = "[]" ]]; then
    return 0
  fi
  printf '%s' "${output}" | awk -v f="${file}" '
    /"RuleID":/ {
      match($0, /"RuleID":[[:space:]]*"[^"]*"/)
      if (RLENGTH > 0) {
        rid = substr($0, RSTART, RLENGTH)
        sub(/^"RuleID":[[:space:]]*"/, "", rid)
        sub(/"$/, "", rid)
        print f "\t1\tgitleaks matched rule '\''" rid "'\''"
      }
    }
  '
}

scan_with_fallback() {
  local file="$1"
  local patterns=(
    'AKIA[0-9A-Z]{16}'
    'ghp_[A-Za-z0-9]{36}'
    'github_pat_[A-Za-z0-9_]{82}'
    'sk-[A-Za-z0-9]{48}'
    'sk-ant-[A-Za-z0-9_-]{80,}'
    'sk_live_[A-Za-z0-9]{24}'
  )
  local cred_pat='(password|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)[[:space:]]*[=:][[:space:]]*["'"'"'][^"'"'"']+["'"'"']'
  local pat hits hit line_no

  for pat in "${patterns[@]}"; do
    if hits="$(grep -En "${pat}" "${file}" 2>/dev/null)"; then
      while IFS= read -r hit; do
        [[ -n "${hit}" ]] || continue
        line_no="${hit%%:*}"
        printf '%s\t%s\tcredential pattern /%s/ matched\n' "${file}" "${line_no}" "${pat}"
      done <<<"${hits}"
    fi
  done

  if hits="$(grep -EniI "${cred_pat}" "${file}" 2>/dev/null)"; then
    while IFS= read -r hit; do
      [[ -n "${hit}" ]] || continue
      line_no="${hit%%:*}"
      printf '%s\t%s\tcredential-shaped variable assignment\n' "${file}" "${line_no}"
    done <<<"${hits}"
  fi
}

scan_file() {
  local file="$1"
  if command -v gitleaks >/dev/null 2>&1; then
    scan_with_gitleaks "${file}"
  else
    scan_with_fallback "${file}"
  fi
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

recipe = os.environ["CHECK_SKILL_RECIPE_SECRET"]

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
                f"{path} line {line_int}: {context}. Committed credentials "
                "leak via git history, build logs, and shoulder-surfed "
                "terminals. Skill files are loaded automatically by Claude — "
                "same exposure as any committed config."
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
  CHECK_SKILL_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SKILL_RECIPE_SECRET="${RECIPE_SECRET}" \
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
