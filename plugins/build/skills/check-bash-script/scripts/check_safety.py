#!/usr/bin/env python3
"""Tier-1 bash safety checker — emits JSON ARRAY of three envelopes.

Three rules:
  - eval (FAIL):       `eval` invocation without justification comment.
  - gnu-flags (WARN):  GNU-only coreutils flags without a declared
                       `requires: gnu-coreutils` header.
  - tmp-literal (FAIL): hardcoded `/tmp/` or `/var/tmp/` string literals.

Exit codes:
  0  — overall_status pass / warn for every emitted envelope
  1  — overall_status=fail for any envelope (eval or tmp-literal hit)
  64 — usage error

Example:
    ./check_safety.py path/to/script.sh path/to/scripts/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
EMIT_CAP = 3
HEADER_SCAN_LINES = 20

_BASH_SHEBANGS = ("#!/usr/bin/env bash", "#!/bin/bash", "#!/usr/bin/env -S bash")
_BASH_EXTENSIONS = (".sh", ".bash")

_EVAL_RE = re.compile(r"(?:^|[\s;&|(`])eval\s")
_EVAL_JUSTIFICATIONS = ("shellcheck disable=SC2294", "eval-justified:")

_GNU_COREUTILS_HEADER_RE = re.compile(r"requires:\s*gnu-coreutils", re.IGNORECASE)

_GNU_FLAG_SIMPLE = [
    (re.compile(r"(?:^|\s)grep\s+(?:-[A-Za-z]*)?P(?:\s|$)"), "grep -P"),
    (re.compile(r"(?:^|\s)readlink\s+-f(?:\s|$)"), "readlink -f"),
    (re.compile(r"(?:^|[^A-Za-z])date\s+-d\s"), "date -d"),
    (re.compile(r"(?:^|\s)stat\s+-c\s"), "stat -c"),
    (re.compile(r"(?:^|\s)xargs\s+(?:-[A-Za-z]*)?r(?:\s|$)"), "xargs -r"),
]
_SED_I_RE = re.compile(r"(?:^|\s)sed\s+-i(?:\s+(?![\"'])|$)")

_TMP_LITERAL_RE = re.compile(r"[\"'](/tmp|/var/tmp)/")  # noqa: S108

_RECIPE_EVAL = (
    "Replace `eval` with `case` for action dispatch, an array for command "
    "construction (`cmd=(...); \"${cmd[@]}\"`), or parameter expansion. "
    "If `eval` is genuinely required (rare, dynamically generated source), "
    "document the rationale with `# shellcheck disable=SC2294 # <reason>` "
    "or `# eval-justified: <reason>` on the same line or the line above.\n\n"
    "Example (case dispatch):\n"
    "    case \"$action\" in\n"
    "      start) start_server ;;\n"
    "      stop)  stop_server  ;;\n"
    "      *)     die \"unknown action: $action\" ;;\n"
    "    esac\n"
)

_RECIPE_GNU_FLAGS = (
    "Either declare `# requires: gnu-coreutils` in the header (so a reader "
    "knows the script targets Linux/Homebrew gnu-coreutils, not BSD/macOS "
    "default `find`/`sed`/`stat`), or rewrite using a portable form. "
    "Common rewrites:\n"
    "  sed -i 's/X/Y/' file\n"
    "    → sed 's/X/Y/' file > file.new && mv file.new file\n"
    "  readlink -f path\n"
    "    → cd \"$(dirname \"$path\")\" && pwd  (or a Python shim)\n"
    "  date -d '<expr>'\n"
    "    → date -j -f <fmt> '<input>'  on macOS; document both branches\n"
    "  stat -c '%s' file\n"
    "    → stat -c '%s' file 2>/dev/null || stat -f '%z' file\n"
)

_RECIPE_TMP_LITERAL = (
    "Replace `/tmp/...` or `/var/tmp/...` literals with `\"$(mktemp)\"` "
    "(file) or `\"$(mktemp -d)\"` (dir), and register a `trap` for cleanup "
    "on the very next line. Hardcoded /tmp paths are racy "
    "(symlink attacks, predictable names) and leak across runs.\n\n"
    "Example:\n"
    "    out=\"$(mktemp)\"\n"
    "    trap 'rm -f \"$out\"' EXIT INT TERM\n"
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
            print(f"check_safety.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _scan_eval(path: Path, lines: list[str]) -> list[dict]:
    findings: list[dict] = []
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            continue
        if not _EVAL_RE.search(line):
            continue
        prev = lines[lineno - 2] if lineno >= 2 else ""
        if any(j in line or j in prev for j in _EVAL_JUSTIFICATIONS):
            continue
        findings.append(
            emit_json_finding(
                rule_id="eval",
                status="fail",
                location={"line": lineno, "context": f"{path}: {line.strip()[:80]}"},
                reasoning=(
                    f"line {lineno} uses `eval` without a justification comment. "
                    "Eval re-parses its argument; if any value flows from input, "
                    "it is a shell injection vector."
                ),
                recommended_changes=_RECIPE_EVAL,
            )
        )
    return findings


def _scan_gnu_flags(path: Path, lines: list[str]) -> list[dict]:
    findings: list[dict] = []
    header = "\n".join(lines[:HEADER_SCAN_LINES])
    if _GNU_COREUTILS_HEADER_RE.search(header):
        return findings
    emitted = 0
    for lineno, line in enumerate(lines, 1):
        if emitted >= EMIT_CAP:
            break
        if line.lstrip().startswith("#"):
            continue
        label: str | None = None
        if _SED_I_RE.search(line):
            label = "sed -i (no backup arg, GNU-only)"
        else:
            for pattern, lbl in _GNU_FLAG_SIMPLE:
                if pattern.search(line):
                    label = lbl
                    break
        if label is None:
            continue
        findings.append(
            emit_json_finding(
                rule_id="gnu-flags",
                status="warn",
                location={"line": lineno, "context": f"{path}: {label}"},
                reasoning=(
                    f"line {lineno} uses GNU-only flag ({label}) without a "
                    "`# requires: gnu-coreutils` header declaring the platform "
                    "contract. Silent macOS/Linux divergence."
                ),
                recommended_changes=_RECIPE_GNU_FLAGS,
            )
        )
        emitted += 1
    return findings


def _scan_tmp_literal(path: Path, lines: list[str]) -> list[dict]:
    findings: list[dict] = []
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            continue
        if _TMP_LITERAL_RE.search(line):
            findings.append(
                emit_json_finding(
                    rule_id="tmp-literal",
                    status="fail",
                    location={
                        "line": lineno,
                        "context": f"{path}: {line.strip()[:80]}",
                    },
                    reasoning=(
                        f"line {lineno} contains a hardcoded /tmp or /var/tmp "
                        "literal. Predictable temp paths are races and "
                        "symlink attacks waiting to happen."
                    ),
                    recommended_changes=_RECIPE_TMP_LITERAL,
                )
            )
    return findings


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_safety.py: cannot read {path}: {err}", file=sys.stderr)
        return
    per_rule["eval"].extend(_scan_eval(path, lines))
    per_rule["gnu-flags"].extend(_scan_gnu_flags(path, lines))
    per_rule["tmp-literal"].extend(_scan_tmp_literal(path, lines))


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_safety.py",
        description="Tier-1 bash safety checker (eval, GNU flags, /tmp literals).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more .sh/.bash files or directories (non-recursive).",
    )
    return parser


_RULE_ORDER = ["eval", "gnu-flags", "tmp-literal"]


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
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
