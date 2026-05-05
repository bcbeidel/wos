#!/usr/bin/env python3
"""Tier-1 bash preflight checker — flags external commands missing `command -v` checks.

Single rule: rule_id="preflight". All findings status="warn" (Tier-1 coaching).
Replaces the preflight portion of the dissolved D3 (subprocess-tool-hygiene).
mktemp/trap pairing and gnu-flags are scripted separately
(check_structure.py and check_safety.py respectively).

Detection algorithm:
  1. First pass — build the set of commands the script preflights.
     A preflight is `command -v <name>` (or `which <name>`, `type -P <name>`,
     `hash <name>`) appearing anywhere in the file.
  2. First pass — build the set of locally-defined functions
     (`name() { ... }` or `function name { ... }`).
  3. Second pass — for each line, identify the leading external command.
     If the command is not a builtin, not a local function, and not in the
     preflight set, surface ONE finding per unique command name (no spam).

Coverage gap (~25%): not detected:
  - Wrappers that themselves preflight (script calls helper, helper preflights)
  - Conditional commands (only invoked on certain branches; preflight could
    be conditional too — judgment call)
  - Commands sourced from external libraries (the source target may
    preflight; we cannot follow it)
  - Commands invoked via `command "$cmd"` or `eval "$line"` (dynamic)
The script flags the high-signal cases; the user reviews edge cases.

Exit codes:
  0  — overall_status pass / warn (WARN-only)
  64 — usage error

Example:
    ./check_preflight.py path/to/script.sh path/to/scripts/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
RULE_ID = "preflight"

_BASH_SHEBANGS = ("#!/usr/bin/env bash", "#!/bin/bash", "#!/usr/bin/env -S bash")
_BASH_EXTENSIONS = (".sh", ".bash")

# Bash builtins, keywords, and reserved words. Anything not here, not locally
# defined, and not preflighted is treated as a missing-preflight candidate.
_BUILTINS = frozenset(
    {
        # Builtins
        "cd", "echo", "printf", "read", "set", "local", "declare", "readonly",
        "unset", "export", "trap", "exit", "return", "shift", "test", "true",
        "false", "type", "builtin", "command", "eval", "exec", "alias",
        "unalias", "source", ".", "let", "wait", "kill", "jobs", "fg", "bg",
        "pwd", "pushd", "popd", "dirs", "history", "fc", "umask", "ulimit",
        "times", "logout", "suspend", "compgen", "complete", "compopt",
        "shopt", "enable", "disable", "help", "mapfile", "readarray",
        "caller", "getopts",
        # Reserved words / keywords
        "if", "then", "elif", "else", "fi", "for", "while", "until", "do",
        "done", "case", "esac", "select", "function", "in", "time",
        # `[` / `[[` / `]]` are operators
        "[", "[[", "]]", "{", "}",
        # Common conventional helpers in toolkit scripts (treated as project-local)
        "die", "usage", "main", "preflight",
    }
)

# command -v <name> and friends — build preflight set.
_PREFLIGHT_RES = (
    re.compile(r"\bcommand\s+-v\s+([\w.-]+)"),
    re.compile(r"(?:^|[\s;&|`(])which\s+([\w.-]+)"),
    re.compile(r"\btype\s+-[Pp]\s+([\w.-]+)"),
    re.compile(r"\bhash\s+([\w.-]+)"),
)

# Local function definitions: `name() { ... }` or `function name { ... }`.
_FUNC_DEF_RES = (
    re.compile(r"^\s*([A-Za-z_][\w-]*)\s*\(\s*\)"),
    re.compile(r"^\s*function\s+([A-Za-z_][\w-]*)\b"),
)

# Leading word: command name at the start of a non-comment, non-blank line.
# Skips assignments (VAR=value), control flow (covered by builtins), and
# leading `$(...)` substitution.
_LEAD_CMD_RE = re.compile(r"^\s*([A-Za-z_][\w.-]*)\b(?!\s*=)")

_RECIPE_PREFLIGHT = (
    "Add a `preflight` function at the top of `main` that verifies every "
    "external command via `command -v <cmd>`. Failing fast with an "
    "actionable message ('missing required commands: jq') beats failing "
    "mid-run with a cryptic 'command not found' deep in the script.\n\n"
    "Example:\n"
    "    readonly REQUIRED_CMDS=(jq curl gzip find)\n"
    "    preflight() {\n"
    "      local cmd missing=()\n"
    "      for cmd in \"${REQUIRED_CMDS[@]}\"; do\n"
    '        command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")\n'
    "      done\n"
    '      [[ "${#missing[@]}" -eq 0 ]] || die "missing: ${missing[*]}"\n'
    "    }\n"
    "    main() {\n"
    "      preflight\n"
    "      do_work\n"
    "    }\n"
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
            print(f"check_preflight.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _scan_file(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_preflight.py: cannot read {path}: {err}", file=sys.stderr)
        return []

    preflighted: set[str] = set()
    local_funcs: set[str] = set()
    for line in lines:
        if line.lstrip().startswith("#"):
            continue
        for r in _PREFLIGHT_RES:
            for m in r.finditer(line):
                preflighted.add(m.group(1))
        for r in _FUNC_DEF_RES:
            m = r.match(line)
            if m:
                local_funcs.add(m.group(1))

    findings: list[dict] = []
    seen_cmds: set[str] = set()
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            continue
        m = _LEAD_CMD_RE.match(line)
        if not m:
            continue
        cmd = m.group(1)
        if cmd in _BUILTINS or cmd in local_funcs or cmd in preflighted:
            continue
        if cmd in seen_cmds:
            continue
        seen_cmds.add(cmd)
        findings.append(
            emit_json_finding(
                rule_id=RULE_ID,
                status="warn",
                location={
                    "line": lineno,
                    "context": f"{path}: external command `{cmd}` first used here",
                },
                reasoning=(
                    f"line {lineno} invokes external command `{cmd}` without "
                    "a `command -v` preflight check earlier in the file. "
                    "Failing fast on missing dependencies surfaces the "
                    "problem before any work happens."
                ),
                recommended_changes=_RECIPE_PREFLIGHT,
            )
        )
    return findings


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_preflight.py",
        description=(
            "Tier-1 bash preflight checker (external commands missing "
            "command -v verification)."
        ),
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
    try:
        files = _collect_targets(args.paths)
    except _UsageError:
        return EXIT_USAGE
    except KeyboardInterrupt:
        return 130

    all_findings: list[dict] = []
    for f in files:
        all_findings.extend(_scan_file(f))

    envelope = emit_rule_envelope(rule_id=RULE_ID, findings=all_findings)
    print_envelope(envelope)
    return 1 if envelope["overall_status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
