#!/usr/bin/env python3
"""Run the discovery layer to regenerate manifests and rules.

Usage:
    python3 scripts/run_discovery.py [--root ROOT]
    python  scripts/run_discovery.py [--root ROOT]

Defaults to the current working directory if --root is not specified.
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate CLAUDE.md manifest, AGENTS.md, and rules file "
        "from context documents on disk."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    args = parser.parse_args()

    from wos.discovery import run_discovery

    run_discovery(args.root)
    print("Discovery complete.")


if __name__ == "__main__":
    main()
