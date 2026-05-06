#!/usr/bin/env python3
"""Tier-1 bash idiom checker — emits JSON ARRAY of three envelopes.

Three rules, all WARN (style coaching):
  - bracket-test:     `[ ... ]` tests where `[[ ... ]]` is preferred.
  - printf-over-echo: `echo -e`/`echo -n`/escape-laden echo (prefer printf).
  - var-braces:       unbraced `$var` of 3+ chars where `${var}` is clearer.

Per-rule emission is capped at 3 findings per file (noise control).
Exit codes: 0 always (WARN-only), 64 on usage error.

Example:
    ./check_idioms.py path/to/script.sh path/to/scripts/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
EMIT_CAP = 3

_BASH_SHEBANGS = ("#!/usr/bin/env bash", "#!/bin/bash", "#!/usr/bin/env -S bash")
_BASH_EXTENSIONS = (".sh", ".bash")

_DOUBLE_BRACKET_RE = re.compile(r"\[\[")
_SINGLE_BRACKET_RE = re.compile(r"(?:^|[\s;&|(])\[\s")
_ECHO_ANTI_RE = re.compile(r"(?:^|[\s;&|(])echo\s+(?:-[en]+|\S*\\[ntr\\])")
_UNBRACED_VAR_RE = re.compile(r"(?<!\$\{)(?<!\\)\$[a-zA-Z_][a-zA-Z0-9_]{2,}")

_RECIPE_BRACKET_TEST = (
    "Replace `[ ... ]` with `[[ ... ]]`. Double-bracket tests do not "
    "word-split on the LHS, support pattern matching (`==` glob), and "
    "support regex (`=~`).\n\n"
    "Example:\n"
    '    if [[ "$x" == "y" ]]; then ...\n'
    '    if [[ "$file" == *.log ]]; then ...\n'
    '    if [[ "$version" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+$ ]]; then ...\n'
)

_RECIPE_PRINTF_OVER_ECHO = (
    "Replace `echo -e`/`echo -n`/escape-bearing `echo` with `printf 'fmt\\n' "
    '"$a" "$b"`. `printf` is portable across shells; `echo`\'s flag handling '
    "varies (-e/-n behave differently on different platforms). `printf` does "
    "not append a newline; supply `\\n` explicitly.\n\n"
    "Example:\n"
    "    printf 'name:\\t%s\\nvalue:\\t%s\\n' \"$name\" \"$value\"\n"
)

_RECIPE_VAR_BRACES = (
    "Brace the expansion when it abuts identifier characters: `${var}foo` "
    "rather than `$varfoo` (which expands `$varfoo`, an unset variable, to "
    "empty). Other adjacent characters (`/`, `.`, `-`, space) do not require "
    "braces.\n\n"
    "Example:\n"
    "    printf '%s\\n' \"${prefix}${timestamp}\"\n"
    "    log_path=\"${dir}${name}_log\"\n"
)

_RULES = [
    {
        "rule_id": "bracket-test",
        "pattern": _SINGLE_BRACKET_RE,
        "skip_if": _DOUBLE_BRACKET_RE,
        "reasoning_suffix": (
            "uses `[ ... ]` (single-bracket); prefer `[[ ... ]]` in bash."
        ),
        "recipe": _RECIPE_BRACKET_TEST,
    },
    {
        "rule_id": "printf-over-echo",
        "pattern": _ECHO_ANTI_RE,
        "skip_if": None,
        "reasoning_suffix": "non-trivial echo (flags/escapes); prefer printf.",
        "recipe": _RECIPE_PRINTF_OVER_ECHO,
    },
    {
        "rule_id": "var-braces",
        "pattern": _UNBRACED_VAR_RE,
        "skip_if": None,
        "reasoning_suffix": (
            "bare-dollar expansion adjacent to identifier characters; brace it."
        ),
        "recipe": _RECIPE_VAR_BRACES,
    },
]


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
            print(f"check_idioms.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _scan_rule(
    path: Path,
    lines: list[str],
    rule: dict,
) -> list[dict]:
    findings: list[dict] = []
    emitted = 0
    pattern = rule["pattern"]
    skip_if = rule["skip_if"]
    for lineno, line in enumerate(lines, 1):
        if emitted >= EMIT_CAP:
            break
        if line.lstrip().startswith("#"):
            continue
        if skip_if is not None and skip_if.search(line):
            continue
        if pattern.search(line):
            findings.append(
                emit_json_finding(
                    rule_id=rule["rule_id"],
                    status="warn",
                    location={
                        "line": lineno,
                        "context": f"{path}: {line.strip()[:80]}",
                    },
                    reasoning=f"line {lineno} {rule['reasoning_suffix']}",
                    recommended_changes=rule["recipe"],
                )
            )
            emitted += 1
    return findings


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_idioms.py: cannot read {path}: {err}", file=sys.stderr)
        return
    for rule in _RULES:
        per_rule[rule["rule_id"]].extend(_scan_rule(path, lines, rule))


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_idioms.py",
        description="Tier-1 bash idiom checker (WARN-only style findings).",
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

    per_rule: dict[str, list[dict]] = {r["rule_id"]: [] for r in _RULES}
    for f in files:
        _scan_file(f, per_rule)

    envelopes = [
        emit_rule_envelope(rule_id=r["rule_id"], findings=per_rule[r["rule_id"]])
        for r in _RULES
    ]
    print_envelope(envelopes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
