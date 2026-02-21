#!/usr/bin/env python3
"""Progressive context scanner — token-efficient discovery.

Usage:
    python3 scripts/scan_context.py index [--area AREA] [--type TYPE] [--root ROOT]
    python3 scripts/scan_context.py outline FILE [--root ROOT]
    python3 scripts/scan_context.py extract FILE SECTION [SECTION ...] [--root ROOT]

Subcommands:
    index    List all context documents (one line per file)
    outline  Show section headings with word counts for a file
    extract  Print raw section content from a file
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_index(args: argparse.Namespace) -> None:
    from wos.models.context_area import ContextArea

    root = str(Path(args.root).resolve())
    areas = ContextArea.scan_all(root)

    for area in areas:
        if args.area and area.name != args.area:
            continue
        for record in area.to_index_records():
            if args.type and record["document_type"] != args.type:
                continue
            print(
                f"{record['path']}  {record['document_type']}  "
                f"{record['title']}  {record['description']}"
            )


def cmd_outline(args: argparse.Namespace) -> None:
    from wos.document_types import parse_document

    root = Path(args.root).resolve()
    file_path = root / args.file
    if not file_path.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    rel_path = args.file
    content = file_path.read_text(encoding="utf-8")
    doc = parse_document(rel_path, content)
    print(doc.to_outline())


def cmd_extract(args: argparse.Namespace) -> None:
    from wos.document_types import parse_document

    root = Path(args.root).resolve()
    file_path = root / args.file
    if not file_path.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    rel_path = args.file
    content = file_path.read_text(encoding="utf-8")
    doc = parse_document(rel_path, content)

    for section_name in args.sections:
        section = doc.get_section(section_name)
        if section is None:
            print(
                f"Error: section '{section_name}' not found in {args.file}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"## {section.name}\n")
        print(section.content)
        print()


def main() -> None:
    # Shared --root argument via parent parser
    root_parser = argparse.ArgumentParser(add_help=False)
    root_parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )

    parser = argparse.ArgumentParser(
        description="Progressive context scanner for token-efficient discovery."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # index
    idx = subparsers.add_parser(
        "index", help="List all context documents", parents=[root_parser]
    )
    idx.add_argument("--area", help="Filter by area name")
    idx.add_argument("--type", help="Filter by document type")

    # outline
    out = subparsers.add_parser(
        "outline", help="Show section headings for a file", parents=[root_parser]
    )
    out.add_argument("file", help="Relative path to document")

    # extract
    ext = subparsers.add_parser(
        "extract", help="Extract section content from a file", parents=[root_parser]
    )
    ext.add_argument("file", help="Relative path to document")
    ext.add_argument("sections", nargs="+", help="Section name(s) to extract")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "outline":
        cmd_outline(args)
    elif args.command == "extract":
        cmd_extract(args)


if __name__ == "__main__":
    main()
