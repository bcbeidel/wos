#!/usr/bin/env python3
"""Run project scaffolding operations.

Usage:
    python3 scripts/run_scaffold.py init --purpose "Description" --areas "a,b"
    python3 scripts/run_scaffold.py area --name "area-name" --description "..."

Defaults to the current working directory if --root is not specified.
"""

from __future__ import annotations

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold project context structure."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init subcommand
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new project"
    )
    init_parser.add_argument(
        "--purpose",
        default=None,
        help="Brief project purpose",
    )
    init_parser.add_argument(
        "--areas",
        required=True,
        help="Comma-separated list of area names",
    )

    # area subcommand
    area_parser = subparsers.add_parser(
        "area", help="Add a domain area"
    )
    area_parser.add_argument(
        "--name",
        required=True,
        help="Area name (will be normalized to lowercase-hyphenated)",
    )
    area_parser.add_argument(
        "--description",
        default=None,
        help="Brief description of what this area covers",
    )

    args = parser.parse_args()

    from wos.scaffold import scaffold_area, scaffold_project

    if args.command == "init":
        areas = [a.strip() for a in args.areas.split(",") if a.strip()]
        result = scaffold_project(args.root, areas, args.purpose)
    else:
        result = scaffold_area(args.root, args.name, args.description)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
