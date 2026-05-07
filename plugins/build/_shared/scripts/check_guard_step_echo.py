#!/usr/bin/env python3
"""Detect step-number echoes in SKILL.md Anti-Pattern Guards bullets.

Anti-Pattern Guards should name failure modes the workflow steps and
Key Instructions do not already mandate. A guard whose body cites
"Step N" / "step #N" / "step 3.5" paraphrases the workflow itself —
process echo. See `plugins/build/_shared/references/skill-best-practices.md`
for the rule.

Usage:
    check_guard_step_echo.py <path> [<path> ...]
    check_guard_step_echo.py --human plugins
    check_guard_step_echo.py --envelope plugins/build/skills/build-rule/SKILL.md

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

_GUARDS_HEADING_RE = re.compile(r"^##\s+Anti-Pattern Guards\s*$", re.MULTILINE)
_NEXT_H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)
_BULLET_RE = re.compile(r"^(\d+)\.\s+", re.MULTILINE)
_STEP_RE = re.compile(r"\bstep\s*#?\d+(\.\d+)?\b", re.IGNORECASE)


def _iter_skill_files(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_file() and p.name == "SKILL.md":
            out.append(p)
        elif p.is_dir():
            out.extend(sorted(p.rglob("SKILL.md")))
    return out


def find_violations(text: str) -> list[dict]:
    """Return [{line, bullet, text}] for each numbered guard bullet whose
    body cites a workflow step number.
    """
    heading_match = _GUARDS_HEADING_RE.search(text)
    if not heading_match:
        return []
    section_start = heading_match.end()
    next_h2 = _NEXT_H2_RE.search(text, section_start)
    section_end = next_h2.start() if next_h2 else len(text)
    section = text[section_start:section_end]
    line_offset = text.count("\n", 0, section_start) + 1

    bullets = list(_BULLET_RE.finditer(section))
    violations: list[dict] = []
    for i, m in enumerate(bullets):
        body_start = m.start()
        body_end = bullets[i + 1].start() if i + 1 < len(bullets) else len(section)
        body = section[body_start:body_end]
        step_match = _STEP_RE.search(body)
        if not step_match:
            continue
        line_in_section = section.count("\n", 0, body_start)
        line_no = line_offset + line_in_section
        first_line = body.splitlines()[0].strip()
        violations.append(
            {
                "line": line_no,
                "bullet": int(m.group(1)),
                "match": step_match.group(0),
                "text": first_line,
            }
        )
    return violations


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flag step-number echoes in SKILL.md Anti-Pattern Guards.",
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
        help="Emit a check-skill-style envelope (rule_id=guard-step-echo).",
    )
    return parser


_RECOMMENDED_CHANGES = (
    "Drop the guard bullet, or rewrite it to name a non-obvious failure "
    "mode the workflow steps cannot prevent on their own. A guard whose "
    "body paraphrases 'Step N' restates the workflow — process echo. See "
    "skill-best-practices.md (Authoring Principles → Anti-Pattern Guards)."
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
                f"Guard bullet #{v['bullet']} cites `{v['match']}` — "
                "process echo of the workflow step it paraphrases."
            ),
            "recommended_changes": _RECOMMENDED_CHANGES,
        }
        for v in violations
    ]
    return {
        "rule_id": "guard-step-echo",
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
            print(
                f"{v['file']}:{v['line']}: guard #{v['bullet']}: "
                f"{v['match']}: {v['text']}"
            )
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
