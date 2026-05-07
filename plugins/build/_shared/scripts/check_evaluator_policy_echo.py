#!/usr/bin/env python3
"""Detect verbatim Evaluator-policy bullets in check-* SKILL.md files.

The canonical Evaluator policy lives in
`plugins/build/_shared/references/check-skill-pattern.md#evaluator-policy`.
A check-* SKILL.md should cite that anchor, not duplicate the bullets.

This detector flags any SKILL.md whose body contains all three sentinel
phrases that uniquely identify the Evaluator-policy bullets:
- "Default-closed when borderline"
- "Severity floor: WARN"
- "One finding per dimension"

All three must appear (boolean AND) before the SKILL.md is flagged. Two
of three is permitted — partial overlap is common in unrelated prose.

Usage:
    check_evaluator_policy_echo.py <path> [<path> ...]
    check_evaluator_policy_echo.py --human plugins
    check_evaluator_policy_echo.py --envelope plugins/build/skills/check-readme/SKILL.md

Each path may be a directory (walked recursively for `SKILL.md`) or a
single `SKILL.md` file. With no paths, walks the current working
directory.

Output: JSON array of violations to stdout (or human-readable lines
with --human, or check-skill envelopes with --envelope). Exit 0 if
clean, 1 if any violations, 2 on read error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SENTINELS = (
    "Default-closed when borderline",
    "Severity floor: WARN",
    "One finding per dimension",
)


def _iter_skill_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file() and p.name == "SKILL.md":
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("SKILL.md")))
    return out


def find_violations(text: str) -> list[dict]:
    """Return [{line, sentinel, text}] for each sentinel hit, but only
    if all three sentinels are present in the text. If fewer than three
    appear, return [] — partial overlap is not a violation.
    """
    hits: list[dict] = []
    for sentinel in _SENTINELS:
        for m in re.finditer(re.escape(sentinel), text):
            line_no = text.count("\n", 0, m.start()) + 1
            line_text = text.splitlines()[line_no - 1].strip()
            hits.append({"line": line_no, "sentinel": sentinel, "text": line_text})
    sentinels_present = {h["sentinel"] for h in hits}
    if len(sentinels_present) < len(_SENTINELS):
        return []
    hits.sort(key=lambda v: v["line"])
    return hits


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flag verbatim Evaluator-policy bullets in check-* SKILL.md.",
    )
    parser.add_argument(
        "paths",
        type=Path,
        nargs="*",
        help="SKILL.md files or directories to walk. Defaults to current dir.",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Emit human-readable lines instead of JSON.",
    )
    parser.add_argument(
        "--envelope",
        action="store_true",
        help="Emit a check-skill-style envelope (rule_id=evaluator-policy-echo).",
    )
    return parser


_RECOMMENDED_CHANGES = (
    "Replace the verbatim Evaluator-policy bullets with a citation to "
    "`_shared/references/check-skill-pattern.md#evaluator-policy`. "
    "The pattern doc is the SSoT; SKILL.md cites, not duplicates."
)


def _build_envelope(violations: list[dict]) -> dict:
    findings = [
        {
            "status": "warn",
            "location": {
                "line": v["line"],
                "context": f"{v['file']}: {v['text']}",
            },
            "reasoning": (
                f"Sentinel `{v['sentinel']}` echoes the canonical "
                "Evaluator-policy bullets in check-skill-pattern.md."
            ),
            "recommended_changes": _RECOMMENDED_CHANGES,
        }
        for v in violations
    ]
    return {
        "rule_id": "evaluator-policy-echo",
        "overall_status": "warn" if findings else "pass",
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = get_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        return int(err.code) if err.code is not None else 0
    paths = args.paths or [Path.cwd()]
    files = _iter_skill_files(paths)
    all_violations: list[dict] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as err:
            print(f"error: cannot read {f}: {err}", file=sys.stderr)
            return 2
        for v in find_violations(text):
            all_violations.append({"file": str(f), **v})
    if args.human:
        for v in all_violations:
            print(f"{v['file']}:{v['line']}: {v['sentinel']}: {v['text']}")
        if all_violations:
            print(
                f"\n{len(all_violations)} violations across "
                f"{len({v['file'] for v in all_violations})} files",
                file=sys.stderr,
            )
    elif args.envelope:
        json.dump(_build_envelope(all_violations), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        json.dump(all_violations, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 1 if all_violations else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
