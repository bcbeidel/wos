#!/usr/bin/env python3
"""Detect the profile of a python script.

Profiles are defined in `plugins/build/_shared/references/python-script-profiles.md`:

  - library:      no shebang AND no `if __name__ == "__main__":` AND no `main(`
  - skill-helper: imports argparse AND uses sys.stdin.read() AND uses json.loads(
  - cli:          default

The detection is best-effort. The `--profile=<name>` flag override always wins.

Usage:
    detect_python_profile.py <path>
    detect_python_profile.py --profile=library <path>

Output: prints the resolved profile name to stdout. Exit 0 on success,
1 on read error, 2 on invalid `--profile` value.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VALID_PROFILES = ("cli", "library", "skill-helper")

_SHEBANG_RE = re.compile(r"^#!\s*\S+python")
_MAIN_GUARD_RE = re.compile(
    r'^if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', re.MULTILINE
)
_MAIN_DEF_RE = re.compile(r"^def\s+main\s*\(", re.MULTILINE)
_ARGPARSE_IMPORT_RE = re.compile(
    r"^(?:import\s+argparse|from\s+argparse\s+import)", re.MULTILINE
)
_STDIN_READ_RE = re.compile(r"sys\.stdin\.read\s*\(")
_JSON_LOADS_RE = re.compile(r"json\.loads?\s*\(")


def detect(text: str) -> str:
    """Return the resolved profile name for the given script source."""
    has_shebang = bool(_SHEBANG_RE.search(text.split("\n", 1)[0])) if text else False
    has_main_guard = bool(_MAIN_GUARD_RE.search(text))
    has_main_def = bool(_MAIN_DEF_RE.search(text))
    if not has_shebang and not has_main_guard and not has_main_def:
        return "library"
    has_argparse = bool(_ARGPARSE_IMPORT_RE.search(text))
    has_stdin_read = bool(_STDIN_READ_RE.search(text))
    has_json_loads = bool(_JSON_LOADS_RE.search(text))
    if has_argparse and has_stdin_read and has_json_loads:
        return "skill-helper"
    return "cli"


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect the profile of a python script.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the python script to inspect.",
    )
    parser.add_argument(
        "--profile",
        choices=VALID_PROFILES,
        default=None,
        help="Override detection. When set, this profile name is printed verbatim.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = get_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        # argparse exits with 2 on invalid arguments — preserve that contract
        return int(err.code) if err.code is not None else 0
    if args.profile is not None:
        print(args.profile)
        return 0
    try:
        text = args.path.read_text(encoding="utf-8")
    except OSError as err:
        print(f"error: cannot read {args.path}: {err}", file=sys.stderr)
        return 1
    print(detect(text))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
