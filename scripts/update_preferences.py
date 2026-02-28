#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Update communication preferences in CLAUDE.md.

Usage:
    uv run scripts/update_preferences.py <file> key=value [key=value ...]

Example:
    uv run scripts/update_preferences.py CLAUDE.md directness=blunt verbosity=terse
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update communication preferences in a target file.",
    )
    parser.add_argument(
        "file",
        help="Target file to update (e.g., CLAUDE.md)",
    )
    parser.add_argument(
        "preferences",
        nargs="+",
        metavar="key=value",
        help="Preference key=value pairs (e.g., directness=blunt)",
    )
    args = parser.parse_args()

    from wos.preferences import update_preferences

    prefs = {}
    for arg in args.preferences:
        if "=" not in arg:
            parser.error(f"Invalid preference: {arg!r} (expected key=value)")
        key, value = arg.split("=", 1)
        prefs[key] = value

    update_preferences(args.file, prefs)
    print(f"Updated preferences in {args.file}")


if __name__ == "__main__":
    main()
