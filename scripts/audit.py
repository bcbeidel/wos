#!/usr/bin/env python3
"""Run WOS validation checks on a project.

Usage:
    python3 scripts/audit.py [--root DIR] [--no-urls] [--json] [--fix]
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path


def _relative_path(file_path: str, root: Path) -> str:
    """Return file_path relative to root, falling back to the original."""
    try:
        return str(Path(file_path).relative_to(root))
    except ValueError:
        return file_path


def main() -> None:
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser(
        description="Run WOS validation checks on a project.",
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
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output issues as JSON",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Regenerate out-of-sync or missing _index.md files",
    )
    args = parser.parse_args()

    # Deferred imports — keeps --help fast
    from wos.index import generate_index
    from wos.validators import validate_project

    root = Path(args.root).resolve()
    issues = validate_project(root, verify_urls=not args.no_urls)

    # --fix: regenerate _index.md files that are out of sync or missing
    if args.fix:
        fixed: list[str] = []
        remaining: list[dict] = []
        for issue in issues:
            file_path = issue["file"]
            msg = issue["issue"]
            if (
                file_path.endswith("_index.md")
                and ("out of sync" in msg or "missing" in msg)
            ):
                idx_path = Path(file_path)
                directory = idx_path.parent
                content = generate_index(directory)
                idx_path.write_text(content, encoding="utf-8")
                fixed.append(file_path)
                print(f"Fixed: {_relative_path(file_path, root)}", file=sys.stderr)
            else:
                remaining.append(issue)
        issues = remaining

    # Output
    if args.json_output:
        print(json.dumps(issues, indent=2))
    elif issues:
        for issue in issues:
            rel = _relative_path(issue["file"], root)
            print(f"[FAIL] {rel}: {issue['issue']}")
        count = len(issues)
        summary = "1 issue found." if count == 1 else f"{count} issues found."
        print(f"\n{summary}")
    else:
        print("All checks passed.")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
