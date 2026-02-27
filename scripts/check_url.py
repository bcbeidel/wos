#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check URL reachability using wos.url_checker.

Usage:
    uv run scripts/check_url.py URL [URL ...]
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
    if len(sys.argv) < 2:
        print("Usage: check_url.py URL [URL ...]", file=sys.stderr)
        sys.exit(1)

    from wos.url_checker import check_urls

    urls = sys.argv[1:]
    results = check_urls(urls)
    for r in results:
        print(json.dumps({
            "url": r.url,
            "reachable": r.reachable,
            "status": r.status,
            "reason": r.reason,
        }))


if __name__ == "__main__":
    main()
