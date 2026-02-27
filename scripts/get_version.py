#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Print the WOS plugin version.

Usage:
    uv run scripts/get_version.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def main() -> None:
    plugin_json = _plugin_root / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        print("plugin.json not found", file=sys.stderr)
        sys.exit(1)

    with open(plugin_json) as f:
        data = json.load(f)
    print(data["version"])


if __name__ == "__main__":
    main()
