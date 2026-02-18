#!/usr/bin/env python3
"""Run auto-fixes on project documents.

Usage:
    python3 scripts/run_auto_fix.py [--root ROOT] [--dry-run]

Reads health report, applies available auto-fixes, and reports results.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-fix health issues in project documents."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without writing changes",
    )
    args = parser.parse_args()

    from wos.auto_fix import apply_auto_fixes, get_fixed_content
    from wos.document_types import parse_document
    from wos.validators import validate_document

    root = Path(args.root).resolve()

    # Find all markdown files in context/ and artifacts/
    search_dirs = [root / "context", root / "artifacts"]
    md_files = []
    for search_dir in search_dirs:
        if search_dir.is_dir():
            md_files.extend(search_dir.rglob("*.md"))

    if not md_files:
        report = {
            "status": "pass",
            "files_checked": 0,
            "fixes": [],
            "message": "No documents found.",
        }
        print(json.dumps(report, indent=2))
        sys.exit(0)

    all_fixes = []

    for md_file in sorted(md_files):
        rel_path = str(md_file.relative_to(root))

        try:
            content = md_file.read_text(encoding="utf-8")
            doc = parse_document(rel_path, content)
        except Exception:
            continue

        issues = validate_document(doc)
        if not issues:
            continue

        results = apply_auto_fixes(
            rel_path, content, issues, dry_run=args.dry_run
        )

        if results and not args.dry_run:
            fixed = get_fixed_content(rel_path, content, issues)
            if fixed:
                md_file.write_text(fixed, encoding="utf-8")

        all_fixes.extend(results)

    report = {
        "status": "dry_run" if args.dry_run else "applied",
        "files_checked": len(md_files),
        "fixes": all_fixes,
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
