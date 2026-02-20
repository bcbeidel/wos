#!/usr/bin/env python3
"""Run health checks on project documents.

Usage:
    python3 scripts/check_health.py [--root ROOT] [--tier2]

Outputs JSON report. Exit code 1 if any issue has severity: fail.
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
    args = parser.parse_args()

    from wos.cross_validators import check_source_url_reachability, run_cross_validators
    from wos.document_types import IssueSeverity, ValidationIssue, parse_document
    from wos.models.health_report import HealthReport
    from wos.tier2_triggers import run_triggers
    from wos.token_budget import estimate_token_budget
    from wos.validators import validate_document

    root = Path(args.root).resolve()
    docs = []
    parse_issues: list[ValidationIssue] = []

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
        report = HealthReport(
            files_checked=0,
            issues=[],
            triggers=[],
            token_budget=estimate_token_budget([]),
        )
        output = report.to_json()
        output["message"] = (
            "No documents found. Use /wos:create-context to initialize your project."
        )
        print(json.dumps(output, indent=2))
        sys.exit(0)

    for md_file in sorted(md_files):
        rel_path = str(md_file.relative_to(root))
        try:
            content = md_file.read_text(encoding="utf-8")
            doc = parse_document(rel_path, content)
            docs.append(doc)
        except Exception as e:
            parse_issues.append(
                ValidationIssue(
                    file=rel_path,
                    issue=f"Failed to parse: {e}",
                    severity=IssueSeverity.FAIL,
                    validator="parse_document",
                    suggestion="Fix frontmatter or document structure",
                )
            )

    # Run per-file validators
    all_issues: list[ValidationIssue] = list(parse_issues)
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
                if i.file == doc.path and i.severity == IssueSeverity.FAIL
            ]
            if not doc_failures:
                all_triggers.extend(run_triggers(doc))

    # Strip the issue from the budget dict (it's already in all_issues)
    budget_output = {k: v for k, v in token_budget.items() if k != "issue"}

    # Build and output report
    report = HealthReport(
        files_checked=len(docs) + len(parse_issues),
        issues=all_issues,
        triggers=all_triggers,
        token_budget=budget_output,
    )

    print(json.dumps(report.to_json(), indent=2))
    sys.exit(1 if report.status == IssueSeverity.FAIL else 0)


if __name__ == "__main__":
    main()
