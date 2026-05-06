#!/usr/bin/env bash
#
# check_deps.sh — Deterministic Tier-1 dependency-declaration check for
# Python scripts. Emits a JSON ARRAY containing one envelope
# (rule_id="declared-deps") per scripts/_common.py.
#
# declared-deps (WARN): when a non-stdlib module is imported, the file
# must declare its dependencies (PEP 723 `# /// script` block,
# colocated requirements.txt, or a top-of-file deps comment).
#
# Thin wrapper around _ast_checks.py deps <file>; helper emits TSV.
#
# Usage:
#   check_deps.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly HELPER="${SCRIPT_DIR}/_ast_checks.py"

readonly REQUIRED_CMDS=(python3 find basename)

readonly _RULE_ORDER="declared-deps"

readonly RECIPE_DECLARED_DEPS='Either add a PEP 723 `# /// script` block at the top of the file, or colocate a `requirements.txt` next to the script. Scripts are expected to be reproducible on a fresh machine; undeclared dependencies mean the next maintainer debugs an `ImportError` before they can debug the actual problem.

PEP 723 (self-contained):

    #!/usr/bin/env python3
    """Fetch exchange rates."""

    # /// script
    # requires-python = ">=3.10"
    # dependencies = ["requests>=2.32"]
    # ///

    import requests

Or a colocated requirements.txt:

    # requirements.txt next to the script
    requests>=2.32
'

usage() {
  cat <<'EOF'
check_deps.sh — Dependency-declaration check for Python scripts.

Usage:
  check_deps.sh <path> [<path> ...]

Check:
  declared-deps  non-stdlib imports must pair with a PEP 723 block,
                 colocated requirements.txt, or top-of-file deps comment.

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
    python3) printf 'brew install python  |  apt install python3  |  dnf install python3' ;;
    find | basename) printf 'should be preinstalled on any POSIX system' ;;
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
  if [[ ! -f "${HELPER}" ]]; then
    printf '%s: helper not found: %s\n' "${PROGNAME}" "${HELPER}" >&2
    exit 69
  fi
}

check_file() {
  python3 "${HELPER}" deps "$1" || true
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    case "${target}" in
      *.py) check_file "${target}" ;;
    esac
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      check_file "${file}"
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
    "declared-deps": os.environ["CHECK_PY_RECIPE_DECLARED_DEPS"],
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
    CHECK_PY_RECIPE_DECLARED_DEPS="${RECIPE_DECLARED_DEPS}" \
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
