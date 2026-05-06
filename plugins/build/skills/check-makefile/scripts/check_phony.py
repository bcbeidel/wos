#!/usr/bin/env python3
"""Tier-1 Makefile .PHONY-coverage checker — emits JSON envelope per `_common`.

Parses target definitions and `.PHONY:` prerequisite lists, then
flags targets that look non-file-producing (no `/`, no `.`, no
variable expansion, no `%` pattern) but are absent from `.PHONY`.

Heuristic: a bare lowercase verb (`build`, `test`, `_helper`) is
phony by convention; a target name containing `/`, `.`, `$(`, or `%`
is presumed file-producing and skipped.

Single-rule script. Emits one envelope: rule_id="phony-coverage".
All findings are status="warn".

Exit codes: 0 on clean / warn, 64 on argument error.

Example:
    ./check_phony.py path/to/Makefile
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _common import emit_json_finding, emit_rule_envelope, print_envelope

EXIT_USAGE = 64
RULE_ID = "phony-coverage"

_TARGET_RE = re.compile(r"^([A-Za-z0-9_./$()%-]+)\s*:(?!=)")
_PHONY_RE = re.compile(r"^\.PHONY\s*:\s*(.*)$")
_SPECIAL_PREFIXES = (".",)
_FILE_INDICATORS = ("/", ".", "$(", "${", "%")

_RECIPE_PHONY_COVERAGE = (
    "Add the missing target(s) to a `.PHONY` prerequisite list (or split "
    "into multiple `.PHONY` lines if grouping aids readability). A file "
    "named `<target>` in the repo silently breaks `make <target>` without "
    "the declaration — Make sees the file, decides the target is up to "
    "date, and does nothing.\n\n"
    "Example:\n"
    "    .PHONY: build test lint\n"
    "\n"
    "    lint:\n"
    "    \truff check .\n"
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
            print(f"check_phony.py: path not found: {target}", file=sys.stderr)
            raise _UsageError
    return files


def _looks_phony(name: str) -> bool:
    if name.startswith(_SPECIAL_PREFIXES):
        return False
    if any(ind in name for ind in _FILE_INDICATORS):
        return False
    return True


def _parse(lines: list[str]) -> tuple[list[tuple[str, int]], set[str]]:
    """Return (ordered list of (target name, line number), set of .PHONY names)."""
    targets: list[tuple[str, int]] = []
    phony: set[str] = set()
    for lineno, line in enumerate(lines, 1):
        if line.startswith("\t"):
            continue
        phony_match = _PHONY_RE.match(line)
        if phony_match:
            for name in phony_match.group(1).split():
                phony.add(name)
            continue
        target_match = _TARGET_RE.match(line)
        if target_match:
            targets.append((target_match.group(1), lineno))
    return targets, phony


def _scan_file(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as err:
        print(f"check_phony.py: cannot read {path}: {err}", file=sys.stderr)
        return []

    targets, phony = _parse(lines)
    findings: list[dict] = []
    seen: set[str] = set()
    for name, lineno in targets:
        if name in seen:
            continue
        seen.add(name)
        if _looks_phony(name) and name not in phony:
            findings.append(
                emit_json_finding(
                    rule_id=RULE_ID,
                    status="warn",
                    location={
                        "line": lineno,
                        "context": f"{path}: target `{name}` not in .PHONY",
                    },
                    reasoning=(
                        f"Target `{name}` looks non-file-producing (no `/`, "
                        "`.`, variable expansion, or `%` pattern) but is "
                        "absent from `.PHONY`. A file named "
                        f"`{name}` in the repo silently breaks "
                        f"`make {name}`."
                    ),
                    recommended_changes=_RECIPE_PHONY_COVERAGE,
                )
            )
    return findings


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_phony.py",
        description="Tier-1 Makefile .PHONY coverage checker.",
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

    all_findings: list[dict] = []
    for f in files:
        all_findings.extend(_scan_file(f))

    envelope = emit_rule_envelope(rule_id=RULE_ID, findings=all_findings)
    print_envelope(envelope)
    return 1 if envelope["overall_status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
