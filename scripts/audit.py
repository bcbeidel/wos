#!/usr/bin/env python3
"""Run WOS validation checks on a project.

Usage:
    python3 scripts/audit.py [--root DIR] [--no-urls] [--json] [--fix]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
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
                print(f"Fixed: {file_path}", file=sys.stderr)
            else:
                remaining.append(issue)
        issues = remaining

    # Output
    if args.json_output:
        print(json.dumps(issues, indent=2))
    elif issues:
        for issue in issues:
            print(f"[FAIL] {issue['file']}: {issue['issue']}")
    else:
        print("All checks passed.")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
