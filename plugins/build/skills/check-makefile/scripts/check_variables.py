#!/usr/bin/env python3
"""Tier-1 Makefile variable-discipline checker — emits JSON ARRAY of two envelopes.

Two rules:
  - assignment-op (WARN):    top-level assignments use `:=`, `?=`, `+=`,
                             not bare `=`, unless a `# deferred:` /
                             `# recursive:` comment is adjacent (same
                             line or previous non-blank line).
  - top-level-shell (WARN):  no `$(shell …)` expansions at top level
                             outside a small allowlist (`git rev-parse`,
                             `git describe`, `uname`, `pwd`, `id -u`,
                             `id -g`).

Top-level = not inside a recipe (no leading tab) and not an
`export`/`override`/conditional directive line.

Exit codes:
  0  — overall_status pass / warn for every emitted envelope
  1  — overall_status=fail (none in this script)
  64 — usage error

Example:
    ./check_variables.py path/to/Makefile
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
PROG = "check_variables.py"

_ASSIGNMENT_RE = re.compile(
    r"^(?:export\s+|override\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(:=|\?=|\+=|!=|::=|=)"
)
_SHELL_CALL_RE = re.compile(r"\$\(shell\s+([^)]+)\)")
_DEFERRED_COMMENT_RE = re.compile(r"#\s*(deferred|recursive)[:\s]", re.IGNORECASE)
_ALLOWED_SHELL = (
    "git rev-parse",
    "git describe",
    "uname",
    "pwd",
    "id -u",
    "id -g",
)

_RECIPE_ASSIGNMENT_OP = (
    "Change to `:=` (immediate evaluation) or `?=` (overridable). Use "
    "bare `=` only when deferred expansion is deliberate, and document "
    "with `# deferred: <reason>` on the same line or the line above. "
    "Recursive `=` re-evaluates its right-hand side every reference, "
    "which surprises performance when the RHS contains `$(shell …)`.\n\n"
    "Example:\n"
    "    PYTHON ?= python3                # overridable from environment\n"
    "    BUILD_DIR := build               # fixed, immediate\n"
    "    # deferred: re-resolve per-target output dir\n"
    "    OUT = $(BUILD_DIR)/$(TARGET)\n"
)

_RECIPE_TOP_LEVEL_SHELL = (
    "Move the `$(shell …)` into a recipe (lazy — only invoked when the "
    "target is built), use a sentinel file, or switch to a cheap "
    "allowlisted command (`git rev-parse`, `git describe`, `uname`, "
    "`pwd`, `id -u`, `id -g`). Top-level `$(shell …)` runs on every "
    "`make` invocation, including `make help`.\n\n"
    "Example:\n"
    "    # Before — runs on every `make`, even `make help`:\n"
    "    #   VERSION := $(shell curl -s https://example.com/version)\n"
    "    \n"
    "    # After — lazy, only when `version` is built:\n"
    "    version:\n"
    "    \t@curl -s https://example.com/version > .version\n"
)

_RULE_ORDER = ["assignment-op", "top-level-shell"]


class _UsageError(Exception):
    pass


def _is_makefile(path: Path) -> bool:
    return path.name in ("Makefile", "GNUmakefile") or path.suffix == ".mk"


def _collect_targets(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in paths:
        if target.is_file():
            if _is_makefile(target):
                files.append(target)
        elif target.is_dir():
            for child in sorted(target.iterdir()):
                if child.is_file() and _is_makefile(child):
                    files.append(child)
        else:
            print(f"{PROG}: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _prev_non_blank(lines: list[str], idx: int) -> str:
    for i in range(idx - 1, -1, -1):
        if lines[i].strip():
            return lines[i]
    return ""


def _has_deferred_justification(lines: list[str], idx: int) -> bool:
    if _DEFERRED_COMMENT_RE.search(lines[idx]):
        return True
    return bool(_DEFERRED_COMMENT_RE.search(_prev_non_blank(lines, idx)))


def _is_shell_allowed(cmd: str) -> bool:
    cmd = cmd.strip().strip('"').strip("'")
    return any(cmd.startswith(allowed) for allowed in _ALLOWED_SHELL)


def _scan_file(path: Path, per_rule: dict[str, list[dict]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"{PROG}: cannot read {path}: {err}", file=sys.stderr)
        return

    for idx, line in enumerate(lines):
        lineno = idx + 1
        if line.startswith("\t"):
            continue
        stripped = line.lstrip()
        if stripped.startswith("#") or not stripped:
            continue

        match = _ASSIGNMENT_RE.match(line)
        if match and match.group(2) == "=":
            if not _has_deferred_justification(lines, idx):
                varname = match.group(1)
                per_rule["assignment-op"].append(
                    emit_json_finding(
                        rule_id="assignment-op",
                        status="warn",
                        location={
                            "line": lineno,
                            "context": f"{path}: {varname} = ...",
                        },
                        reasoning=(
                            f"line {lineno}: top-level variable {varname!r} "
                            "uses bare `=` without a `# deferred:` / "
                            "`# recursive:` justification. Default to `:=` "
                            "or `?=`."
                        ),
                        recommended_changes=_RECIPE_ASSIGNMENT_OP,
                    )
                )

        for shell_match in _SHELL_CALL_RE.finditer(line):
            cmd = shell_match.group(1)
            if not _is_shell_allowed(cmd):
                per_rule["top-level-shell"].append(
                    emit_json_finding(
                        rule_id="top-level-shell",
                        status="warn",
                        location={
                            "line": lineno,
                            "context": f"{path}: $(shell {cmd.strip()[:60]})",
                        },
                        reasoning=(
                            f"line {lineno}: `$(shell {cmd.strip()[:40]})` "
                            "runs at parse time on every `make` invocation, "
                            "including `make help`. Move into a recipe or "
                            "use a sentinel."
                        ),
                        recommended_changes=_RECIPE_TOP_LEVEL_SHELL,
                    )
                )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Tier-1 Makefile variable-discipline checker (2 rules)."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="path",
        help="One or more Makefile / *.mk files or directories (non-recursive).",
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
