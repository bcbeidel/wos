#!/usr/bin/env python3
"""Detect Receives/Produces boilerplate in SKILL.md Handoff sections.

The canonical Handoff section shape contains only `**Chainable to:**`.
`**Receives:**` restates `argument-hint:` frontmatter; `**Produces:**`
restates the `<output_format>` heading. See
`plugins/build/_shared/references/skill-best-practices.md` for the rule.

Usage:
    check_handoff_shape.py <path> [<path> ...]
    check_handoff_shape.py --human plugins
    check_handoff_shape.py --human plugins/build/skills/build-skill/SKILL.md

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

_HANDOFF_HEADING_RE = re.compile(r"^##\s+Handoff\s*$", re.MULTILINE)
_NEXT_H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)
_RECEIVES_RE = re.compile(r"^\*\*Receives:\*\*", re.MULTILINE)
_PRODUCES_RE = re.compile(r"^\*\*Produces:\*\*", re.MULTILINE)


def _iter_skill_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file() and p.name == "SKILL.md":
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("SKILL.md")))
    return out


def find_violations(text: str) -> list[dict]:
    """Return [{line, kind, text}] for each Receives/Produces inside Handoff."""
    heading_match = _HANDOFF_HEADING_RE.search(text)
    if not heading_match:
        return []
    section_start = heading_match.end()
    next_h2 = _NEXT_H2_RE.search(text, section_start)
    section_end = next_h2.start() if next_h2 else len(text)
    section = text[section_start:section_end]
    line_offset = text.count("\n", 0, section_start) + 1
    violations: list[dict] = []
    for kind, pattern in (("receives", _RECEIVES_RE), ("produces", _PRODUCES_RE)):
        for m in pattern.finditer(section):
            line_in_section = section.count("\n", 0, m.start())
            line_no = line_offset + line_in_section
            line_text = section.splitlines()[line_in_section].strip()
            violations.append({"line": line_no, "kind": kind, "text": line_text})
    violations.sort(key=lambda v: v["line"])
    return violations


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flag Receives/Produces in SKILL.md Handoff sections.",
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
        help="Emit a check-skill-style envelope (rule_id=handoff-shape).",
    )
    return parser


_RECOMMENDED_CHANGES = (
    "Remove the **Receives:** and/or **Produces:** lines from the "
    "## Handoff section. Keep only **Chainable to:**. See "
    "skill-best-practices.md (Authoring Principles → Handoff section)."
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
                f"`**{v['kind'].capitalize()}:**` line in ## Handoff "
                f"duplicates frontmatter or output-format heading."
            ),
            "recommended_changes": _RECOMMENDED_CHANGES,
        }
        for v in violations
    ]
    return {
        "rule_id": "handoff-shape",
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
            print(f"{v['file']}:{v['line']}: {v['kind']}: {v['text']}")
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
