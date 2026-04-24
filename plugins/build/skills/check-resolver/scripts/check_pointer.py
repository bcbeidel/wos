#!/usr/bin/env python3
"""Deterministic Tier-1 checks for the AGENTS.md pointer in a resolver artifact.

Two checks per target repo root:

- **pointer-present** — AGENTS.md contains a reference to RESOLVER.md.
  Text match on the literal "RESOLVER.md". FAIL on miss.
- **pointer-resolves** — the RESOLVER.md the pointer names exists on disk.
  Resolved relative to the repo root. FAIL on miss.

Absence of AGENTS.md itself produces one FAIL under pointer-present
(there is nothing to anchor from).

Example:
    ./check_pointer.py .
    ./check_pointer.py /path/to/repo-a /path/to/repo-b
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXIT_USAGE = 2
EXIT_INTERRUPTED = 130

POINTER_MARKER = "RESOLVER.md"
AGENTS_FILENAME = "AGENTS.md"
RESOLVER_FILENAME = "RESOLVER.md"


def emit_fail(path: Path, check: str, detail: str, recommendation: str) -> None:
    print(f"FAIL  {path} — {check}: {detail}")
    print(f"  Recommendation: {recommendation}")


def check_pointer_present(agents_path: Path) -> bool:
    if not agents_path.is_file():
        emit_fail(
            agents_path,
            "pointer-present",
            f"{AGENTS_FILENAME} does not exist at repo root",
            f"Create {AGENTS_FILENAME} with a one-line pointer to {RESOLVER_FILENAME}",
        )
        return False
    try:
        text = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"error: cannot read {agents_path}: {err}", file=sys.stderr)
        return False
    if POINTER_MARKER not in text:
        emit_fail(
            agents_path,
            "pointer-present",
            f"{AGENTS_FILENAME} does not reference {POINTER_MARKER}",
            "Add a one-line pointer directing Claude to consult RESOLVER.md "
            "before filing new content",
        )
        return False
    return True


def check_pointer_resolves(repo_root: Path) -> bool:
    resolver_path = repo_root / RESOLVER_FILENAME
    if not resolver_path.is_file():
        emit_fail(
            repo_root / AGENTS_FILENAME,
            "pointer-resolves",
            f"{POINTER_MARKER} referenced in AGENTS.md but "
            f"{resolver_path} does not exist",
            f"Create {RESOLVER_FILENAME} at the repo root, "
            "or correct the AGENTS.md pointer to the file's actual location",
        )
        return False
    return True


def check_repo(repo_root: Path) -> bool:
    if not repo_root.is_dir():
        print(f"error: not a directory: {repo_root}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    agents_path = repo_root / AGENTS_FILENAME
    ok = True
    if not check_pointer_present(agents_path):
        ok = False
        return ok
    if not check_pointer_resolves(repo_root):
        ok = False
    return ok


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Tier-1 deterministic checks for the AGENTS.md → RESOLVER.md pointer."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="One or more repo-root paths (defaults to current directory).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        all_ok = True
        for repo_root in args.paths:
            if not check_repo(repo_root):
                all_ok = False
        return 0 if all_ok else 1
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
