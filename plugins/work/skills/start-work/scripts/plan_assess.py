#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Assess plan document state for skill execution and resumption.

Usage:
    python plugins/work/skills/start-work/scripts/plan_assess.py --file PATH
    python plugins/work/skills/start-work/scripts/plan_assess.py \\
        --scan [--root DIR] [--subdir PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Locate the sibling wiki plugin via fixed `__file__` navigation.
# plugins/work/skills/start-work/scripts/ → start-work → skills → work → plugins
_wiki_root = Path(__file__).resolve().parent.parent.parent.parent.parent / "wiki"
_wiki_marker = _wiki_root / "src" / "wiki" / "__init__.py"
# Defense-in-depth: only insert the resolved root into sys.path if it
# actually looks like the wiki plugin. Marker check is the import-shadowing
# guardrail.
if _wiki_marker.is_file() and str(_wiki_root) not in sys.path:
    sys.path.insert(0, str(_wiki_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assess plan document state.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        help="Assess a single plan document",
    )
    group.add_argument(
        "--scan",
        action="store_true",
        help="Find all executing plans",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--subdir",
        default=".plans",
        help="Subdirectory to scan (default: .plans)",
    )
    args = parser.parse_args()

    from wiki.plan import PlanDocument

    if args.file:
        result = PlanDocument.assess(args.file)
    else:
        root = str(Path(args.root).resolve())
        result = PlanDocument.scan(root, subdir=args.subdir)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
