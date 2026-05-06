#!/usr/bin/env bash
#
# check_structure.sh — Deterministic Tier-1 structural checks for
# Python scripts. Emits a JSON ARRAY of six envelopes (rule_id="shebang",
# "guard-missing", "guard-shape", "syntax", "main-returns",
# "keyboard-interrupt") per scripts/_common.py.
#
# Thin wrapper around _ast_checks.py structure <file>; helper emits TSV
# to stdout, this script aggregates and reshapes to the unified envelope
# pattern.
#
# Severity ladder:
#   shebang             FAIL
#   guard-missing       FAIL
#   guard-shape         FAIL
#   syntax              FAIL
#   main-returns        WARN
#   keyboard-interrupt  WARN
#
# (`exec-bit` was previously INFO; INFO is not in the envelope pattern,
# so the check no longer emits — see _ast_checks.py:check_exec_bit.)
#
# Usage:
#   check_structure.sh <path> [<path> ...]
#
# Paths may be .py files or directories (top-level .py only).
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

readonly _RULE_ORDER="shebang,guard-missing,guard-shape,syntax,main-returns,keyboard-interrupt"

readonly RECIPE_SHEBANG='Replace the first line with `#!/usr/bin/env python3`. No other first-line form is accepted; hardcoded paths (`/usr/bin/python`) break virtualenvs and `/opt/homebrew/bin/python3` is not portable. `env` resolves the active Python from `PATH`, including virtualenv-activated shells.'

readonly RECIPE_GUARD_MISSING='Add a `__main__` guard at the module bottom that invokes `sys.exit(main())`:

    if __name__ == "__main__":
        sys.exit(main())

Without the guard, importing the script runs its body as a side effect — breaking testability and turning `import myscript` into an execution event.'

readonly RECIPE_GUARD_SHAPE='Replace the guard body with `sys.exit(main())`:

    if __name__ == "__main__":
        sys.exit(main())

`main()` returns an int by convention; without `sys.exit`, the return value is dropped and the exit code is always 0 regardless of error paths.'

readonly RECIPE_SYNTAX='Fix the Python syntax error named in the finding. The file cannot be evaluated further — no other Tier-1 check runs on an unparseable file, and Tier-2 judgment is skipped. Verify with `python3 -c "import ast; ast.parse(open(<path>).read())"`.'

readonly RECIPE_MAIN_RETURNS='Annotate the `main()` signature as `-> int` and ensure every code path returns a concrete int:

    def main(argv: list[str] | None = None) -> int:
        args = get_parser().parse_args(argv)
        return run(args)

The `sys.exit(main())` contract only works when `main()` actually returns an exit code.'

readonly RECIPE_KEYBOARD_INTERRUPT='Wrap the body of `main()` in a `try` that catches `KeyboardInterrupt` and returns `130`:

    def main(argv: list[str] | None = None) -> int:
        args = get_parser().parse_args(argv)
        try:
            return run(args)
        except KeyboardInterrupt:
            return 130

A script that dumps a traceback on Ctrl+C is user-hostile. Exit code 130 is the shell convention for SIGINT-terminated processes.'

usage() {
  cat <<'EOF'
check_structure.sh — Structural checks for Python scripts.

Usage:
  check_structure.sh <path> [<path> ...]

Checks:
  shebang             first line is exactly '#!/usr/bin/env python3'  (FAIL)
  guard-missing       '__main__' guard exists                          (FAIL)
  guard-shape         guard invokes sys.exit(main())                   (FAIL)
  syntax              file parses as Python                            (FAIL)
  main-returns        main() signature declares '-> int'               (WARN)
  keyboard-interrupt  main() has 'except KeyboardInterrupt' handler    (WARN)

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

# Helper emits TSV directly. Suppress its exit code; we derive ours from
# the aggregated envelopes.
check_file() {
  python3 "${HELPER}" structure "$1" || true
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
    "shebang": os.environ["CHECK_PY_RECIPE_SHEBANG"],
    "guard-missing": os.environ["CHECK_PY_RECIPE_GUARD_MISSING"],
    "guard-shape": os.environ["CHECK_PY_RECIPE_GUARD_SHAPE"],
    "syntax": os.environ["CHECK_PY_RECIPE_SYNTAX"],
    "main-returns": os.environ["CHECK_PY_RECIPE_MAIN_RETURNS"],
    "keyboard-interrupt": os.environ["CHECK_PY_RECIPE_KEYBOARD_INTERRUPT"],
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
    CHECK_PY_RECIPE_SHEBANG="${RECIPE_SHEBANG}" \
    CHECK_PY_RECIPE_GUARD_MISSING="${RECIPE_GUARD_MISSING}" \
    CHECK_PY_RECIPE_GUARD_SHAPE="${RECIPE_GUARD_SHAPE}" \
    CHECK_PY_RECIPE_SYNTAX="${RECIPE_SYNTAX}" \
    CHECK_PY_RECIPE_MAIN_RETURNS="${RECIPE_MAIN_RETURNS}" \
    CHECK_PY_RECIPE_KEYBOARD_INTERRUPT="${RECIPE_KEYBOARD_INTERRUPT}" \
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
