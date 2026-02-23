#!/usr/bin/env python3
"""Regenerate all _index.md files in a WOS project.

Usage:
    python3 scripts/reindex.py [--root DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate all _index.md files in a WOS project.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    args = parser.parse_args()

    # Deferred import — keeps --help fast
    from wos.index import generate_index

    root = Path(args.root).resolve()

    # Check that at least one content directory exists
    context_dir = root / "context"
    artifacts_dir = root / "artifacts"

    if not context_dir.is_dir() and not artifacts_dir.is_dir():
        print(
            "No context/ or artifacts/ directory found "
            f"under {root}",
            file=sys.stderr,
        )
        sys.exit(1)

    count = 0

    for subdir in (context_dir, artifacts_dir):
        if not subdir.is_dir():
            continue

        # Also index the top-level subdir itself
        if _reindex_directory(subdir, generate_index):
            count += 1

        # Walk all subdirectories
        for dirpath in sorted(subdir.rglob("*")):
            if not dirpath.is_dir():
                continue
            if _reindex_directory(dirpath, generate_index):
                count += 1

    print(f"Wrote {count} _index.md files.")


def _reindex_directory(directory: Path, generate_index_fn) -> bool:
    """Regenerate _index.md for a single directory if it has content.

    A directory has content if it contains .md files (other than _index.md)
    or subdirectories.

    Returns:
        True if _index.md was written, False if skipped.
    """
    has_md_files = any(
        f.suffix == ".md" and f.name != "_index.md"
        for f in directory.iterdir()
        if f.is_file()
    )
    has_subdirs = any(d.is_dir() for d in directory.iterdir())

    if not has_md_files and not has_subdirs:
        return False

    index_path = directory / "_index.md"
    content = generate_index_fn(directory)
    index_path.write_text(content, encoding="utf-8")
    print(index_path)
    return True


if __name__ == "__main__":
    main()
