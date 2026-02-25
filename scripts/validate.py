#!/usr/bin/env python3
"""Validate a single WOS document.

Usage:
    python3 scripts/validate.py <file> [--root DIR] [--no-urls]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure `import wos` works whether pip-installed or run from plugin cache.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def _relative_path(file_path: str, root: Path) -> str:
    """Return file_path relative to root, falling back to the original."""
    try:
        return str(Path(file_path).relative_to(root))
    except ValueError:
        return file_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a single WOS document.",
    )
    parser.add_argument(
        "file",
        help="Path to the .md file to validate",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--no-urls",
        action="store_true",
        help="Skip URL reachability checks",
    )
    args = parser.parse_args()

    # Deferred imports — keeps --help fast
    from wos.validators import validate_file

    root = Path(args.root).resolve()
    file_path = Path(args.file).resolve()
    issues = validate_file(file_path, root, verify_urls=not args.no_urls)

    if issues:
        for issue in issues:
            rel = _relative_path(issue["file"], root)
            msg = issue["issue"]
            # Relativize any embedded absolute paths in the message
            abs_path = issue["file"]
            if abs_path in msg:
                msg = msg.replace(abs_path, rel)
            print(f"[FAIL] {rel}: {msg}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
