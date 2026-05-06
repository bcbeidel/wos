#!/usr/bin/env bash
#
# check_dangerous_patterns.sh — Tier-1 scan for unverified remote-exec
# and destructive commands inside shell code blocks. Emits a JSON
# ARRAY of two envelopes (rule_id="remote-exec",
# rule_id="destructive-cmd") per scripts/_common.py.
#
# remote-exec (WARN):     curl|bash, wget|bash, eval $(curl ...),
#                         source <(curl ...) and variants.
# destructive-cmd (WARN): rm -rf, dd if=, DROP TABLE, DROP DATABASE,
#                         TRUNCATE, force-push, mv without -i / -n.
#
# Both emit WARN — destructive commands are often legitimate when
# gated; remote-exec is discouraged but occasionally needed (pinned +
# hash-verified). Tier-2 D7 Safety Gating judges the gate.
#
# Scope: only matches inside fenced code blocks whose language tag is
# bash / sh / zsh / shell / console (or untagged).
#
# Usage:
#   check_dangerous_patterns.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (WARN only)
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

readonly RECIPE_REMOTE_EXEC='Pin the upstream version and verify a hash, or install via the package manager. FROM `curl -fsSL https://example.com/install.sh | bash`; TO `curl -fsSL https://example.com/install.sh -o install.sh && echo "<sha256> install.sh" | sha256sum --check && bash install.sh`. Remote-exec is a supply-chain vector; an unpinned pipe-to-shell trusts whatever the upstream serves at fetch time.'

readonly RECIPE_DESTRUCTIVE_CMD='Precede the destructive operation with an explicit approval gate or convert to a dry-run default. FROM `rm -rf ./build/`; TO a 2-step sequence: (1) ask the user to confirm; (2) on confirmation, run the destructive command. Destructive commands are often legitimate when gated but dangerous when ungated — D7 Safety Gating judges whether the gate exists.'

usage() {
  cat <<'EOF'
check_dangerous_patterns.sh — Remote-exec and destructive-command scan.

Usage:
  check_dangerous_patterns.sh <path> [<path> ...]

Detects (in shell code blocks only):
  remote-exec       curl | bash, wget | bash, eval $(curl ...),
                    source <(curl ...)
  destructive-cmd   rm -rf, dd if=, DROP TABLE, TRUNCATE, force-push,
                    mv without -i / -n

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings (WARN only)
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

# TSV: <rule_id>\t<file>\t<line>\t<context>
scan_file() {
  local file="$1"
  awk -v f="${file}" '
    function is_shell_tag(tag) {
      if (tag == "") return 1
      return tag == "bash" || tag == "sh" || tag == "zsh" || tag == "shell" || tag == "console"
    }
    BEGIN { in_fence = 0; shell_fence = 0 }
    {
      line = $0
      if (line ~ /^[[:space:]]*```/) {
        if (!in_fence) {
          in_fence = 1
          tag = line; sub(/^[[:space:]]*```/, "", tag); sub(/[[:space:]]+$/, "", tag)
          shell_fence = is_shell_tag(tag) ? 1 : 0
        } else { in_fence = 0; shell_fence = 0 }
        next
      }
      if (line ~ /^[[:space:]]*~~~/) {
        if (!in_fence) {
          in_fence = 1
          tag = line; sub(/^[[:space:]]*~~~/, "", tag); sub(/[[:space:]]+$/, "", tag)
          shell_fence = is_shell_tag(tag) ? 1 : 0
        } else { in_fence = 0; shell_fence = 0 }
        next
      }
      if (!in_fence || !shell_fence) next

      if (line ~ /curl[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(bash|sh|zsh)/) {
        printf "remote-exec\t%s\t%d\tcurl piped to a shell at line %d\n", f, NR, NR
      }
      if (line ~ /wget[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(bash|sh|zsh)/) {
        printf "remote-exec\t%s\t%d\twget piped to a shell at line %d\n", f, NR, NR
      }
      if (line ~ /eval[[:space:]]*\$\([[:space:]]*curl/) {
        printf "remote-exec\t%s\t%d\teval $(curl ...) pattern at line %d\n", f, NR, NR
      }
      if (line ~ /eval[[:space:]]*\$\([[:space:]]*wget/) {
        printf "remote-exec\t%s\t%d\teval $(wget ...) pattern at line %d\n", f, NR, NR
      }
      if (line ~ /source[[:space:]]+<\([[:space:]]*curl/) {
        printf "remote-exec\t%s\t%d\tsource <(curl ...) pattern at line %d\n", f, NR, NR
      }
      if (line ~ /\.[[:space:]]+<\([[:space:]]*curl/) {
        printf "remote-exec\t%s\t%d\t. <(curl ...) pattern at line %d\n", f, NR, NR
      }

      if (line ~ /(^|[^A-Za-z0-9_])rm[[:space:]]+(-[A-Za-z]*r[A-Za-z]*f|-[A-Za-z]*f[A-Za-z]*r|-rf|-fr)/) {
        printf "destructive-cmd\t%s\t%d\trm -rf variant at line %d\n", f, NR, NR
      }
      if (line ~ /(^|[^A-Za-z0-9_])dd[[:space:]]+[^#]*if=/) {
        printf "destructive-cmd\t%s\t%d\tdd if= (can overwrite devices) at line %d\n", f, NR, NR
      }
      if (line ~ /DROP[[:space:]]+TABLE[[:space:]]+/) {
        printf "destructive-cmd\t%s\t%d\tSQL DROP TABLE at line %d\n", f, NR, NR
      }
      if (line ~ /DROP[[:space:]]+DATABASE[[:space:]]+/) {
        printf "destructive-cmd\t%s\t%d\tSQL DROP DATABASE at line %d\n", f, NR, NR
      }
      if (line ~ /(^|[^A-Za-z0-9_])TRUNCATE[[:space:]]+/) {
        printf "destructive-cmd\t%s\t%d\tSQL TRUNCATE at line %d\n", f, NR, NR
      }
      if (line ~ /git[[:space:]]+push[[:space:]]+[^#]*(-f([[:space:]]|$)|--force([[:space:]=]|$))/) {
        printf "destructive-cmd\t%s\t%d\tgit push --force at line %d\n", f, NR, NR
      }
      if (line ~ /(^|[^A-Za-z0-9_])mv[[:space:]]+/ \
          && line !~ /mv[[:space:]]+(-[^[:space:]]*[in]|--interactive|--no-clobber)/ \
          && line !~ /mv[[:space:]]+(-{1,2}help|-{1,2}version)/) {
        printf "destructive-cmd\t%s\t%d\tmv without -i / -n safety flag at line %d\n", f, NR, NR
      }
    }
  ' "${file}"
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
    "remote-exec": os.environ["CHECK_SKILL_RECIPE_REMOTE_EXEC"],
    "destructive-cmd": os.environ["CHECK_SKILL_RECIPE_DESTRUCTIVE_CMD"],
}
order = ["remote-exec", "destructive-cmd"]

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
            status="warn",
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
    CHECK_SKILL_RECIPE_REMOTE_EXEC="${RECIPE_REMOTE_EXEC}" \
    CHECK_SKILL_RECIPE_DESTRUCTIVE_CMD="${RECIPE_DESTRUCTIVE_CMD}" \
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
