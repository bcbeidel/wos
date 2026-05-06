#!/usr/bin/env python3
"""Tier-1 Makefile recipe-indent checker — emits ONE JSON envelope.

One rule:
  - tab-indent (FAIL): every recipe line starts with a real tab.

Approach: after every target-definition line, treat subsequent
indented lines as the target's recipe block. A blank line or an
un-indented line ends the block. Within the block, any line whose
leading whitespace contains a space (not a tab) is flagged.

Space-indented recipes do not parse — Make rejects with `missing
separator`. All findings are FAIL.

Exit codes:
  0  — overall_status pass
  1  — overall_status=fail (any space-indented recipe line)
  64 — usage error

Example:
    ./check_indent.py path/to/Makefile
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
PROG = "check_indent.py"

_TARGET_RE = re.compile(r"^([A-Za-z0-9_./$()%-]+)\s*:(?!=)")

_RECIPE_TAB_INDENT = (
    "Replace the leading spaces with a single real tab on every recipe "
    "line. Make syntactically requires a tab as the recipe prefix "
    "(unless `.RECIPEPREFIX` is redefined, which is discouraged) — "
    "spaces break parsing outright with `missing separator`.\n\n"
    "Example:\n"
    "    build:\n"
    "    \t$(PYTHON) -m build\n"
)


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


def _scan_file(path: Path, findings: list[dict]) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"{PROG}: cannot read {path}: {err}", file=sys.stderr)
        return

    in_recipe = False
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            in_recipe = False
            continue
        if _TARGET_RE.match(line) and not line.startswith((" ", "\t")):
            in_recipe = True
            continue
        if in_recipe:
            if line.startswith("\t"):
                continue
            if line.startswith(" "):
                findings.append(
                    emit_json_finding(
                        rule_id="tab-indent",
                        status="fail",
                        location={
                            "line": lineno,
                            "context": f"{path}: recipe line starts with spaces",
                        },
                        reasoning=(
                            f"line {lineno} of recipe block starts with spaces, "
                            "not a tab. Make rejects space-indented recipes with "
                            "`missing separator`."
                        ),
                        recommended_changes=_RECIPE_TAB_INDENT,
                    )
                )
                continue
            in_recipe = False


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Tier-1 Makefile recipe-indent checker (1 rule)."
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

    findings: list[dict] = []
    for f in files:
        _scan_file(f, findings)

    envelope = emit_rule_envelope(rule_id="tab-indent", findings=findings)
    print_envelope(envelope)
    return 1 if envelope["overall_status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
