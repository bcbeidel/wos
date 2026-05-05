#!/usr/bin/env python3
"""Tier-1 bash lint check wrapping `shellcheck` — emits JSON ARRAY of 15 envelopes.

Runs shellcheck on each target with a curated rule selector, parses the JSON
output, maps each SC code to one of 15 toolkit rule_ids, and emits one
envelope per rule_id (empty findings for rules that did not fire).

shellcheck is optional — when absent, every envelope is emitted with
overall_status="inapplicable" and exits 0. Other Tier-1 scripts continue
to run.

SC code → rule_id mapping:
  SC2086 → unquoted-variable-expansion        (fail)
  SC2046 → unquoted-command-substitution      (fail)
  SC2068 → unquoted-args-expansion            (fail)
  SC2294 → eval-of-array                      (fail)
  SC2010 → ls-grep-parsing                    (fail)
  SC2012 → ls-instead-of-find                 (fail)
  SC2045 → iterating-ls-output                (fail)
  SC2154 → referenced-but-not-assigned        (warn)
  SC2155 → unscoped-function-variable         (warn)
  SC2006 → backtick-command-substitution      (warn)
  SC2013 → for-line-in-cat                    (warn)
  SC2162 → read-without-r                     (warn)
  SC2038 → find-xargs-without-print0          (warn)
  SC2164 → cd-without-exit-handling           (warn)
  SC2002 → useless-cat                        (warn)

Exit codes:
  0  — overall_status pass / warn / inapplicable for every envelope
  1  — any envelope has overall_status=fail
  64 — usage error

Example:
    ./check_shellcheck.py path/to/script.sh path/to/scripts/
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
SHELLCHECK_CMD = "shellcheck"

_BASH_SHEBANGS = ("#!/usr/bin/env bash", "#!/bin/bash", "#!/usr/bin/env -S bash")
_BASH_EXTENSIONS = (".sh", ".bash")

# SC code → (rule_id, severity)
_SC_TO_RULE: dict[str, tuple[str, str]] = {
    "SC2086": ("unquoted-variable-expansion", "fail"),
    "SC2046": ("unquoted-command-substitution", "fail"),
    "SC2068": ("unquoted-args-expansion", "fail"),
    "SC2294": ("eval-of-array", "fail"),
    "SC2010": ("ls-grep-parsing", "fail"),
    "SC2012": ("ls-instead-of-find", "fail"),
    "SC2045": ("iterating-ls-output", "fail"),
    "SC2154": ("referenced-but-not-assigned", "warn"),
    "SC2155": ("unscoped-function-variable", "warn"),
    "SC2006": ("backtick-command-substitution", "warn"),
    "SC2013": ("for-line-in-cat", "warn"),
    "SC2162": ("read-without-r", "warn"),
    "SC2038": ("find-xargs-without-print0", "warn"),
    "SC2164": ("cd-without-exit-handling", "warn"),
    "SC2002": ("useless-cat", "warn"),
}

# Order must match _SC_TO_RULE insertion order (Python 3.7+ preserves it),
# but pin explicitly so the output array is stable.
_RULE_ORDER = [v[0] for v in _SC_TO_RULE.values()]
_INCLUDED_CODES = tuple(_SC_TO_RULE.keys())

_RECIPES: dict[str, str] = {
    "unquoted-variable-expansion": (
        'Quote every variable expansion: `"$var"`. For arrays use '
        '`"${arr[@]}"` (one argument per element). Unquoted expansion '
        "word-splits on IFS and globs filenames — the largest source of "
        "real-world Bash bugs.\n\n"
        "Example:\n"
        '    for f in "${files[@]}"; do\n'
        '      process "$f"\n'
        "    done\n"
    ),
    "unquoted-command-substitution": (
        'Wrap every `$(...)` expansion in double quotes when used as an '
        'argument or value: `"$(cmd)"`. Same word-split / glob hazard as '
        "variable expansion.\n\n"
        "Example:\n"
        '    cd "$(pwd)/subdir"\n'
        '    process_file "$(find_input_path)"\n'
    ),
    "unquoted-args-expansion": (
        'Always quote `$@` when forwarding arguments: `cmd "$@"`. Use '
        '`"$*"` only for joining into a log message — it concatenates '
        "the array into one string with the first IFS char.\n\n"
        "Example:\n"
        "    run_with_logging() {\n"
        "      printf 'starting: %s\\n' \"$*\" >&2\n"
        '      "$@"\n'
        "    }\n"
    ),
    "eval-of-array": (
        'Remove the `eval`. `"${cmd[@]}"` already preserves argument '
        "boundaries; `eval` re-parses them, discarding the array form's "
        "protection.\n\n"
        "Example:\n"
        '    cmd=(rm -rf "$user_input")\n'
        '    "${cmd[@]}"\n'
    ),
    "ls-grep-parsing": (
        "Replace `ls | grep PATTERN` with a bash glob (`*.log`) or "
        "`find . -name 'PATTERN'`. `ls` output is for humans — programmatic "
        "parsing breaks on whitespace and newlines.\n\n"
        "Example:\n"
        "    files=( *.log )\n"
        '    for f in "${files[@]}"; do process "$f"; done\n'
    ),
    "ls-instead-of-find": (
        "Replace `ls -l | awk` parsing with `stat -c`/`stat -f` (single "
        "file) or `find -printf` (recursive). `ls -l` columns vary across "
        "BSD/GNU.\n\n"
        "Example:\n"
        '    size=$(stat -c \'%s\' "$file" 2>/dev/null '
        '|| stat -f \'%z\' "$file")\n'
        "    find . -maxdepth 1 -type f -printf '%s %p\\n'\n"
    ),
    "iterating-ls-output": (
        "Replace `for f in $(ls PATTERN)` with `for f in PATTERN`. "
        "Use `shopt -s nullglob` to make unmatched globs expand to "
        "nothing (otherwise the literal pattern leaks through).\n\n"
        "Example:\n"
        "    shopt -s nullglob\n"
        "    for f in *.log; do\n"
        '      process "$f"\n'
        "    done\n"
        "    shopt -u nullglob\n"
    ),
    "referenced-but-not-assigned": (
        "For required external inputs use `${var:?msg}`; for optional "
        "use `${var:-default}`; for variables sourced from another file "
        "add `# shellcheck source=path/to/helpers.sh` so shellcheck can "
        "follow the assignment.\n\n"
        "Example:\n"
        "    config_path=\"${config_path:-/etc/myapp/config.yml}\"\n"
        '    process "${config_path:?config_path required}"\n'
    ),
    "unscoped-function-variable": (
        "Split `local var=$(cmd)` into `local var; var=\"$(cmd)\"` so the "
        "substitution's exit status is preserved under `set -e`. The "
        "combined form swallows the inner failure (local always returns 0).\n\n"
        "Example:\n"
        "    some_function() {\n"
        "      local result\n"
        '      result="$(some_cmd)"\n'
        '      process "$result"\n'
        "    }\n"
    ),
    "backtick-command-substitution": (
        'Replace `` `cmd` `` with `"$(cmd)"`. Mechanical and safe; '
        "dollar-paren is nestable, more readable, and the canonical form.\n\n"
        "Example:\n"
        "    count=\"$(wc -l < file)\"\n"
        '    result="$(grep pattern "$(find . -name \'*.txt\')")"\n'
    ),
    "for-line-in-cat": (
        "Replace `for line in $(cat file)` with "
        "`while IFS= read -r line; do ...; done < file`. The `for-cat` "
        "form word-splits and globs each line — broken on whitespace, "
        "broken on filenames containing wildcards.\n\n"
        "Example:\n"
        "    while IFS= read -r line; do\n"
        '      process "$line"\n'
        "    done < file\n"
    ),
    "read-without-r": (
        "Add `-r` to every `read` that processes input lines. Without "
        "`-r`, `read` interprets backslashes — `\\n` becomes `n`. "
        "Canonical iteration: `while IFS= read -r line`.\n\n"
        "Example:\n"
        "    while IFS= read -r line; do\n"
        '      process "$line"\n'
        "    done < file\n"
    ),
    "find-xargs-without-print0": (
        "Pair `-print0` with `xargs -0`, or prefer `find ... -exec cmd "
        "{} +`. Without null-separation, filenames containing spaces or "
        "newlines split into multiple arguments.\n\n"
        "Example:\n"
        "    find . -name '*.log' -print0 | xargs -0 rm\n"
        "    find . -name '*.log' -exec rm {} +\n"
    ),
    "cd-without-exit-handling": (
        "Add `|| exit` to every `cd` (or `|| return 1` inside a "
        "function); never run destructive ops after an unguarded `cd`. "
        "A failed `cd` followed by `rm -rf *` has destroyed real systems.\n\n"
        "Example:\n"
        "    cd /some/dir || exit\n"
        "    rm -rf *\n"
    ),
    "useless-cat": (
        "Replace `cat file | cmd` with `cmd file` (when supported) or "
        "`< file cmd` (preserves left-to-right reading). One less fork "
        "and the lint signal stays clean.\n\n"
        "Example:\n"
        "    grep pattern file\n"
        "    < file grep pattern\n"
    ),
}

_INSTALL_HINT = (
    "Install shellcheck — 'brew install shellcheck' (macOS), "
    "'apt install shellcheck' (Debian/Ubuntu), 'dnf install ShellCheck' (Fedora)."
)


class _UsageError(Exception):
    pass


def _is_bash_script(path: Path) -> bool:
    if path.suffix in _BASH_EXTENSIONS:
        return True
    try:
        first = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    if not first:
        return False
    return any(first[0] == s or first[0].startswith(s) for s in _BASH_SHEBANGS)


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_bash_script(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_bash_script(child):
                    files.append(child)
        else:
            print(f"check_shellcheck.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _run_shellcheck(target: Path) -> list[dict]:
    include = ",".join(_INCLUDED_CODES)
    try:
        result = subprocess.run(
            [SHELLCHECK_CMD, f"--include={include}", "--format=json", str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as err:
        print(f"check_shellcheck.py: cannot exec shellcheck: {err}", file=sys.stderr)
        return []
    if not result.stdout.strip():
        return []
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as err:
        print(
            f"check_shellcheck.py: malformed shellcheck output for {target}: {err}",
            file=sys.stderr,
        )
        return []
    return parsed if isinstance(parsed, list) else []


def _scan_file(target: Path, per_rule: dict[str, list[dict]]) -> None:
    for finding in _run_shellcheck(target):
        code_num = finding.get("code")
        if code_num is None:
            continue
        code = f"SC{code_num}"
        if code not in _SC_TO_RULE:
            continue
        rule_id, severity = _SC_TO_RULE[code]
        message = (finding.get("message") or "").rstrip()
        lineno = int(finding.get("line", 0) or 0) or 1
        per_rule[rule_id].append(
            emit_json_finding(
                rule_id=rule_id,
                status=severity,
                location={"line": lineno, "context": f"{target}: {code} {message}"},
                reasoning=(
                    f"shellcheck {code} at line {lineno}: {message}"
                ),
                recommended_changes=_RECIPES[rule_id],
            )
        )


def _emit_inapplicable_array() -> list[dict]:
    return [
        emit_rule_envelope(rule_id=r, findings=[], inapplicable=True)
        for r in _RULE_ORDER
    ]


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_shellcheck.py",
        description="Tier-1 bash lint check via shellcheck (15-rule curated set).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more .sh/.bash files or directories (non-recursive).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    if shutil.which(SHELLCHECK_CMD) is None:
        print_envelope(_emit_inapplicable_array())
        print(f"INFO: shellcheck not installed; {_INSTALL_HINT}", file=sys.stderr)
        return 0
    try:
        files = _collect_targets(args.paths)
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130

    per_rule: dict[str, list[dict]] = {r: [] for r in _RULE_ORDER}
    for f in files:
        _scan_file(f, per_rule)

    envelopes = [
        emit_rule_envelope(rule_id=r, findings=per_rule[r]) for r in _RULE_ORDER
    ]
    print_envelope(envelopes)
    any_fail = any(e["overall_status"] == "fail" for e in envelopes)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
