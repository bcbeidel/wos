#!/usr/bin/env bash
#
# check_argparse.sh — Deterministic Tier-1 argparse / subprocess checks
# for Python scripts. Emits a JSON ARRAY of three envelopes
# (rule_id="argparse-when-argv", "add-argument-help",
# "subprocess-check") per scripts/_common.py.
#
# argparse-when-argv (WARN): argparse imported when sys.argv accessed
#                            past [0].
# add-argument-help  (WARN): every add_argument() carries a non-empty
#                            help=.
# subprocess-check   (WARN): subprocess.run() sets check=True or
#                            inspects the result.
#
# Thin wrapper around _ast_checks.py argparse <file>; helper emits TSV
# to stdout.
#
# Usage:
#   check_argparse.sh <path> [<path> ...]
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

readonly _RULE_ORDER="argparse-when-argv,add-argument-help,subprocess-check"

readonly RECIPE_ARGPARSE_WHEN_ARGV='Replace manual `sys.argv` slicing with an `argparse`-based parser inside a `get_parser()` function:

    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Input file.")
    parser.add_argument("output", type=Path, help="Output file.")
    args = parser.parse_args()

`argparse` provides `--help`, type coercion, and usage errors that manual slicing can never match. Users who run the script wrong deserve a useful error, not an `IndexError` traceback.'

readonly RECIPE_ADD_ARGUMENT_HELP='Add a `help=` string to every `add_argument` call that lacks one. The `help=` string is what the user sees on `--help`; no string means no documentation.

FROM:
    parser.add_argument("--out", type=Path)

TO:
    parser.add_argument("--out", type=Path, help="Output path.")
'

readonly RECIPE_SUBPROCESS_CHECK='Add `check=True` to the `subprocess.run()` call, or assign the result and inspect `result.returncode` explicitly. Without `check=True`, a non-zero exit from the child process is silently ignored and the script continues as if nothing went wrong.

FROM:
    subprocess.run(["git", "pull"])

TO:
    subprocess.run(["git", "pull"], check=True)
'

usage() {
  cat <<'EOF'
check_argparse.sh — argparse / subprocess checks for Python scripts.

Usage:
  check_argparse.sh <path> [<path> ...]

Checks:
  argparse-when-argv  argparse imported when sys.argv accessed past [0]  (WARN)
  add-argument-help   every add_argument() carries a non-empty help=     (WARN)
  subprocess-check    subprocess.run() sets check=True or inspects rc    (WARN)

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
  python3 "${HELPER}" argparse "$1" || true
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
    "argparse-when-argv": os.environ["CHECK_PY_RECIPE_ARGPARSE_WHEN_ARGV"],
    "add-argument-help": os.environ["CHECK_PY_RECIPE_ADD_ARGUMENT_HELP"],
    "subprocess-check": os.environ["CHECK_PY_RECIPE_SUBPROCESS_CHECK"],
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
    CHECK_PY_RECIPE_ARGPARSE_WHEN_ARGV="${RECIPE_ARGPARSE_WHEN_ARGV}" \
    CHECK_PY_RECIPE_ADD_ARGUMENT_HELP="${RECIPE_ADD_ARGUMENT_HELP}" \
    CHECK_PY_RECIPE_SUBPROCESS_CHECK="${RECIPE_SUBPROCESS_CHECK}" \
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
