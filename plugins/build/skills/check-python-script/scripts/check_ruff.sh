#!/usr/bin/env bash
#
# check_ruff.sh — Deterministic Tier-1 lint / format check for Python
# scripts, wrapping the external `ruff` tool. Emits a JSON ARRAY of 13
# envelopes (one per rule_id) per scripts/_common.py.
#
# Ruff is optional — when absent, every envelope is emitted with
# overall_status="inapplicable" (missing-tool degradation) and the
# script exits 0.
#
# rule_id          severity  ruff codes
#   ruff-D100              WARN  D100
#   ruff-E722              FAIL  E722
#   ruff-SIM115            WARN  SIM115
#   ruff-PLW1514           WARN  PLW1514
#   ruff-PTH               WARN  PTH*
#   ruff-shell-true        FAIL  S602, S604      (consolidated)
#   ruff-S307              FAIL  S307
#   ruff-F401              WARN  F401
#   ruff-ANN               WARN  ANN*
#   ruff-F403              FAIL  F403
#   ruff-S108              FAIL  S108
#   ruff-fstring-modernize WARN  UP031, UP032    (consolidated)
#   ruff-format            WARN  format-drift    (separate ruff invocation)
#
# Usage:
#   check_ruff.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (including when ruff is absent)
#   1   one or more FAIL findings
#   64  usage error
#   69  missing dependency (python3 / awk — not ruff)

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly REQUIRED_CMDS=(awk find basename python3)

readonly RUFF_SELECT="D100,E722,SIM115,PLW1514,PTH,S602,S604,S307,F401,ANN,F403,S108,UP031,UP032"

readonly _RULE_ORDER="ruff-D100,ruff-E722,ruff-SIM115,ruff-PLW1514,ruff-PTH,ruff-shell-true,ruff-S307,ruff-F401,ruff-ANN,ruff-F403,ruff-S108,ruff-fstring-modernize,ruff-format"

readonly RECIPE_RUFF_D100='Add a module docstring as the first statement, naming the script purpose and one example invocation.

    #!/usr/bin/env python3
    """Fetch exchange rates and write them to a CSV.

    Example:
        ./fetch_rates.py --source usd --target eur --out rates.csv
    """

The docstring is the first thing a reader sees and often the only documentation a one-off script has.'

readonly RECIPE_RUFF_E722='Replace `except:` with a specific exception type, or with `except Exception as err:` at the top-level `main()` if a catch-all is intended. Bare `except:` swallows `KeyboardInterrupt` and `SystemExit` and hides real bugs.

FROM:
    try:
        run(args)
    except:
        print("failed")

TO:
    try:
        run(args)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
'

readonly RECIPE_RUFF_SIM115='Wrap the `open()` call in a `with` block so cleanup runs on exceptions. An exception between `open` and `close` leaves the file handle dangling; the context manager guarantees cleanup.

FROM:
    f = open(path)
    data = f.read()
    f.close()

TO:
    with open(path, encoding="utf-8") as f:
        data = f.read()
'

readonly RECIPE_RUFF_PLW1514='Add `encoding="utf-8"` to the `open()` call. The default encoding is platform-dependent; on a Windows CI runner, a file that works locally on macOS silently corrupts non-ASCII characters.

FROM: with open(path) as f:
TO:   with open(path, encoding="utf-8") as f:
'

readonly RECIPE_RUFF_PTH='Rewrite the `os.path` operation using `pathlib.Path`. `pathlib.Path` removes a class of string-manipulation bugs and reads more clearly.

FROM:
    if os.path.exists(os.path.join(dirname, filename)):
        ...

TO:
    if (Path(dirname) / filename).exists():
        ...
'

readonly RECIPE_RUFF_SHELL_TRUE='Replace `shell=True` with a list of arguments. Shell injection is trivial when interpolated input reaches `shell=True`; argument lists pass through `execvp`, not a shell parser, and are injection-safe. (Both ruff S602 and S604 flag this pattern.)

FROM: subprocess.run(f"grep {pattern} {file}", shell=True)
TO:   subprocess.run(["grep", pattern, file])
'

readonly RECIPE_RUFF_S307='Replace `eval` / `exec` with a targeted parser — `json.loads`, `ast.literal_eval`, or an explicit dispatch table. `eval` / `exec` on external input is an RCE vector.

FROM: result = eval(user_input)
TO:   result = ast.literal_eval(user_input)

Or, for dispatch:

    ACTIONS = {"start": start, "stop": stop}
    ACTIONS[action_name](args)
'

readonly RECIPE_RUFF_F401='Remove the import. Unused imports confuse readers and slow startup. If the import exists for a side effect, add an explicit comment naming the side effect.

FROM: import json  # not used anywhere
TO:   (line deleted)
'

readonly RECIPE_RUFF_ANN='Add type annotations to parameters and return type. Start with `main()` and script-boundary functions; interior helpers are optional but encouraged. Type hints are documentation that does not drift and enable static analysis.

FROM: def run(args):
TO:   def run(args: argparse.Namespace) -> int:
'

readonly RECIPE_RUFF_F403='Replace the wildcard with explicit named imports. Wildcard imports pollute the namespace and impede static analysis.

FROM: from utils import *
TO:   from utils import load_config, write_report
'

readonly RECIPE_RUFF_S108='Replace with a `tempfile` call. Hand-constructed `/tmp/` paths race against other processes creating the same name and expose symlink-attack surface; `tempfile` handles both.

FROM: tmp = f"/tmp/work_{os.getpid()}"

TO:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ...
'

readonly RECIPE_RUFF_FSTRING_MODERNIZE='Rewrite as an f-string. f-strings are clearer, faster at runtime, and harder to mis-quote. (Both ruff UP031 and UP032 flag this pattern.)

FROM: "hello, %s" % name      |  "hello, {}".format(name)
TO:   f"hello, {name}"
'

readonly RECIPE_RUFF_FORMAT='Run `ruff format <path>` against the file. Formatter compliance eliminates style bikeshedding and keeps diffs legible. Drift from the formatter output is a mechanical signal, not a judgment call.'

usage() {
  cat <<'EOF'
check_ruff.sh — Ruff-backed lint and format check for Python scripts.

Usage:
  check_ruff.sh <path> [<path> ...]

Ruff is optional. When absent, every envelope is emitted with
overall_status="inapplicable" and the script exits 0.

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings
  1   one or more FAIL findings
  64  usage error
  69  missing required dependency (not ruff)
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

# Map a raw ruff code (e.g. `S602`, `PTH123`, `ANN001`) to (rule_id, status).
# Output: "<rule_id>\t<status>" or empty if the code is not in our set.
map_code() {
  local code="$1"
  case "${code}" in
    D100) printf 'ruff-D100\twarn' ;;
    E722) printf 'ruff-E722\tfail' ;;
    SIM115) printf 'ruff-SIM115\twarn' ;;
    PLW1514) printf 'ruff-PLW1514\twarn' ;;
    PTH*) printf 'ruff-PTH\twarn' ;;
    S602 | S604) printf 'ruff-shell-true\tfail' ;;
    S307) printf 'ruff-S307\tfail' ;;
    F401) printf 'ruff-F401\twarn' ;;
    ANN*) printf 'ruff-ANN\twarn' ;;
    F403) printf 'ruff-F403\tfail' ;;
    S108) printf 'ruff-S108\tfail' ;;
    UP031 | UP032) printf 'ruff-fstring-modernize\twarn' ;;
    *) ;;
  esac
}

# TSV emit: <rule_id>\t<status>\t<file>\t<line>\t<context>
emit_for_file() {
  local target="$1"
  local raw path lineno col code message rest mapped rule_id status

  while IFS= read -r raw; do
    case "${raw}" in
      "" | "Found "* | "All checks passed"* | "warning:"* | "error:"*) continue ;;
    esac
    path="${raw%%:*}"
    rest="${raw#*:}"
    lineno="${rest%%:*}"
    rest="${rest#*:}"
    col="${rest%%:*}"
    rest="${rest#*:}"
    rest="${rest# }"
    code="${rest%% *}"
    message="${rest#* }"

    mapped="$(map_code "${code}")"
    if [[ -z "${mapped}" ]]; then
      continue
    fi
    rule_id="${mapped%%	*}"
    status="${mapped##*	}"
    printf '%s\t%s\t%s\t%s\t%s %s (col %s)\n' \
      "${rule_id}" "${status}" "${path}" "${lineno}" "${code}" "${message}" "${col}"
  done < <(
    ruff check --no-cache --output-format=concise \
      --select="${RUFF_SELECT}" "${target}" 2>/dev/null || true
  )

  # Format drift — separate invocation.
  if ! ruff format --check --no-cache "${target}" >/dev/null 2>&1; then
    printf 'ruff-format\twarn\t%s\t1\tformatter drift detected\n' "${target}"
  fi
}

scan_path() {
  local target="$1"
  local file
  if [[ -f "${target}" ]]; then
    case "${target}" in
      *.py) emit_for_file "${target}" ;;
    esac
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      emit_for_file "${file}"
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
    "ruff-D100": os.environ["CHECK_PY_RECIPE_RUFF_D100"],
    "ruff-E722": os.environ["CHECK_PY_RECIPE_RUFF_E722"],
    "ruff-SIM115": os.environ["CHECK_PY_RECIPE_RUFF_SIM115"],
    "ruff-PLW1514": os.environ["CHECK_PY_RECIPE_RUFF_PLW1514"],
    "ruff-PTH": os.environ["CHECK_PY_RECIPE_RUFF_PTH"],
    "ruff-shell-true": os.environ["CHECK_PY_RECIPE_RUFF_SHELL_TRUE"],
    "ruff-S307": os.environ["CHECK_PY_RECIPE_RUFF_S307"],
    "ruff-F401": os.environ["CHECK_PY_RECIPE_RUFF_F401"],
    "ruff-ANN": os.environ["CHECK_PY_RECIPE_RUFF_ANN"],
    "ruff-F403": os.environ["CHECK_PY_RECIPE_RUFF_F403"],
    "ruff-S108": os.environ["CHECK_PY_RECIPE_RUFF_S108"],
    "ruff-fstring-modernize": os.environ["CHECK_PY_RECIPE_RUFF_FSTRING_MODERNIZE"],
    "ruff-format": os.environ["CHECK_PY_RECIPE_RUFF_FORMAT"],
}

inapplicable = os.environ.get("CHECK_PY_INAPPLICABLE") == "1"

if inapplicable:
    envelopes = [emit_rule_envelope(rule_id=r, findings=[], inapplicable=True) for r in order]
    print_envelope(envelopes)
    sys.exit(0)

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
    CHECK_PY_INAPPLICABLE="${1:-0}" \
    CHECK_PY_RECIPE_RUFF_D100="${RECIPE_RUFF_D100}" \
    CHECK_PY_RECIPE_RUFF_E722="${RECIPE_RUFF_E722}" \
    CHECK_PY_RECIPE_RUFF_SIM115="${RECIPE_RUFF_SIM115}" \
    CHECK_PY_RECIPE_RUFF_PLW1514="${RECIPE_RUFF_PLW1514}" \
    CHECK_PY_RECIPE_RUFF_PTH="${RECIPE_RUFF_PTH}" \
    CHECK_PY_RECIPE_RUFF_SHELL_TRUE="${RECIPE_RUFF_SHELL_TRUE}" \
    CHECK_PY_RECIPE_RUFF_S307="${RECIPE_RUFF_S307}" \
    CHECK_PY_RECIPE_RUFF_F401="${RECIPE_RUFF_F401}" \
    CHECK_PY_RECIPE_RUFF_ANN="${RECIPE_RUFF_ANN}" \
    CHECK_PY_RECIPE_RUFF_F403="${RECIPE_RUFF_F403}" \
    CHECK_PY_RECIPE_RUFF_S108="${RECIPE_RUFF_S108}" \
    CHECK_PY_RECIPE_RUFF_FSTRING_MODERNIZE="${RECIPE_RUFF_FSTRING_MODERNIZE}" \
    CHECK_PY_RECIPE_RUFF_FORMAT="${RECIPE_RUFF_FORMAT}" \
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

  # Ruff is optional — emit all envelopes as inapplicable and exit 0.
  if ! command -v ruff >/dev/null 2>&1; then
    printf '' | emit_envelopes 1
    exit 0
  fi

  local target rc=0
  {
    for target in "$@"; do
      scan_path "${target}"
    done
  } | emit_envelopes 0 || rc=$?
  exit "${rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
