#!/usr/bin/env python3
"""Run health checks on project documents.

Usage:
    python3 scripts/check_health.py [--root ROOT] [--tier2] [--detailed|--json] [--no-color]

Default output is human-readable text. Use --json for machine-readable JSON.
Exit code 1 if any issue has severity: fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate project documents and report issues."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--tier2",
        action="store_true",
        help="Include Tier 2 LLM trigger pre-screening",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed output grouped by severity with suggestions",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON (machine-readable)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color in text output",
    )
    args = parser.parse_args()

    if args.detailed and args.json:
        parser.error("--detailed and --json are mutually exclusive")

    from wos.cross_validators import check_source_url_reachability, run_cross_validators
    from wos.document_types import parse_document
    from wos.tier2_triggers import run_triggers
    from wos.token_budget import estimate_token_budget
    from wos.validators import validate_document

    root = Path(args.root).resolve()
    docs = []
    parse_issues = []

    # Find and parse all markdown files in context/ and artifacts/
    search_dirs = [
        root / "context",
        root / "artifacts",
    ]

    md_files = []
    for search_dir in search_dirs:
        if search_dir.is_dir():
            md_files.extend(search_dir.rglob("*.md"))

    if not md_files:
        report = {
            "status": "pass",
            "files_checked": 0,
            "token_budget": estimate_token_budget([]),
            "issues": [],
            "triggers": [],
            "message": "No documents found. "
            "Use /wos:setup to initialize your project.",
        }
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            from wos.formatting import format_detailed, format_summary

            use_color = not args.no_color and sys.stdout.isatty()
            if args.detailed:
                print(format_detailed(report, color=use_color), end="")
            else:
                print(format_summary(report, color=use_color), end="")
        sys.exit(0)

    for md_file in sorted(md_files):
        rel_path = str(md_file.relative_to(root))
        try:
            content = md_file.read_text(encoding="utf-8")
            doc = parse_document(rel_path, content)
            docs.append(doc)
        except Exception as e:
            parse_issues.append({
                "file": rel_path,
                "issue": f"Failed to parse: {e}",
                "severity": "fail",
                "validator": "parse_document",
                "section": None,
                "suggestion": "Fix frontmatter or document structure",
            })

    # Run per-file validators
    all_issues = list(parse_issues)
    for doc in docs:
        all_issues.extend(validate_document(doc))

    # Run cross-file validators
    all_issues.extend(run_cross_validators(docs, str(root)))

    # Compute token budget for context files only
    context_docs = [d for d in docs if d.path.startswith("context/")]
    token_budget = estimate_token_budget(context_docs)
    if "issue" in token_budget:
        all_issues.append(token_budget["issue"])

    # Run Tier 2 source URL reachability if requested
    if args.tier2:
        all_issues.extend(
            check_source_url_reachability(docs, str(root))
        )

    # Run Tier 2 triggers if requested
    all_triggers = []
    if args.tier2:
        for doc in docs:
            # Skip T2 for files with T1 failures
            doc_failures = [
                i for i in all_issues
                if i["file"] == doc.path and i["severity"] == "fail"
            ]
            if not doc_failures:
                all_triggers.extend(run_triggers(doc))

    # Determine overall status
    severities = [i["severity"] for i in all_issues]
    if "fail" in severities:
        status = "fail"
    elif "warn" in severities:
        status = "warn"
    else:
        status = "pass"

    # Strip the issue from the budget dict (it's already in all_issues)
    budget_output = {k: v for k, v in token_budget.items() if k != "issue"}

    report = {
        "status": status,
        "files_checked": len(docs) + len(parse_issues),
        "token_budget": budget_output,
        "issues": all_issues,
        "triggers": all_triggers,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        from wos.formatting import format_detailed, format_summary

        use_color = not args.no_color and sys.stdout.isatty()
        if args.detailed:
            print(format_detailed(report, color=use_color), end="")
        else:
            print(format_summary(report, color=use_color), end="")

    sys.exit(1 if status == "fail" else 0)


if __name__ == "__main__":
    main()
