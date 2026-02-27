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

import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: update_preferences.py <file> key=value [key=value ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    from wos.preferences import update_preferences

    target_file = sys.argv[1]
    prefs = {}
    for arg in sys.argv[2:]:
        if "=" not in arg:
            print(f"Invalid preference: {arg!r} (expected key=value)", file=sys.stderr)
            sys.exit(1)
        key, value = arg.split("=", 1)
        prefs[key] = value

    update_preferences(target_file, prefs)
    print(f"Updated preferences in {target_file}")


if __name__ == "__main__":
    main()
