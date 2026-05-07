#!/usr/bin/env python3
"""Count quoted trigger phrases in SKILL.md `description:` fields.

For each SKILL.md path, parse YAML frontmatter, extract the `description:`
field (handling block-scalar `>`/`>-`/`|` and inline forms), and count
double-quoted substrings. Output one TAB-separated line per file:

    <path>\\t<count>

Exit 0 when every file is read successfully. Exit 1 with a stderr message
if any file fails to read or has no parseable frontmatter.

Example:
    ./count_triggers.py plugins/*/skills/*/SKILL.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)
_FIELD_START_RE = re.compile(r"^[A-Za-z][\w-]*\s*:")
_DESC_START_RE = re.compile(r"^description\s*:\s*(.*)$")
_QUOTED_RE = re.compile(r'"([^"]+)"')


def extract_description(text: str) -> str | None:
    """Return the textual content of the `description:` frontmatter field.

    Returns None when the file has no YAML frontmatter or no `description:`
    field. Handles three YAML scalar forms:

      description: inline string
      description: "inline quoted"
      description: >
        folded
        block
    """
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return None
    frontmatter = match.group(1)
    parts: list[str] = []
    in_desc = False
    for line in frontmatter.splitlines():
        if not in_desc:
            m = _DESC_START_RE.match(line)
            if not m:
                continue
            in_desc = True
            tail = m.group(1).strip()
            if tail in {">", "|", ">-", "|-", ">+", "|+"}:
                # block scalar — content is on following indented lines
                continue
            if tail.startswith(("'", '"')) and tail.endswith(tail[0]):
                tail = tail[1:-1]
            parts.append(tail)
            continue
        # inside description — stop at next top-level field or end
        if _FIELD_START_RE.match(line):
            break
        if line.strip() == "":
            continue
        parts.append(line.strip())
    if not in_desc:
        return None
    return " ".join(parts)


def count_triggers(text: str) -> int:
    return len(_QUOTED_RE.findall(text))


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count quoted trigger phrases in SKILL.md description fields.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more SKILL.md paths.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    failed = False
    for path in args.paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as err:
            print(f"error: cannot read {path}: {err}", file=sys.stderr)
            failed = True
            continue
        desc = extract_description(text)
        if desc is None:
            print(f"error: {path}: no description field", file=sys.stderr)
            failed = True
            continue
        print(f"{path}\t{count_triggers(desc)}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
