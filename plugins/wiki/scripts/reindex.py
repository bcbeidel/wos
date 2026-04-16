#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Create _index.md files in directories containing managed documents.

For each directory that contains .md files (excluding _index.md itself),
writes a <dir>/_index.md with a table of files and their descriptions.
Also updates the AGENTS.md areas table, preserving existing descriptions.

Usage:
    python3 scripts/reindex.py --root .
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import _bootstrap  # noqa: F401 — side effect: adds src/ to sys.path  # isort: skip


_SKIP = frozenset({
    "node_modules", "__pycache__", "venv", ".venv",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
})


def _read_frontmatter_field(path: Path, field: str) -> str:
    """Read a single scalar field from YAML frontmatter (stdlib-only)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    if not text.startswith("---"):
        return ""
    end = text.find("---", 3)
    if end == -1:
        return ""
    fm = text[3:end]
    for line in fm.splitlines():
        if line.startswith(f"{field}:"):
            value = line[len(field) + 1:].strip()
            # Strip optional inline quotes
            if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            return value
    return ""


def _write_index(directory: Path, root: Path) -> None:
    """Write <directory>/_index.md listing all .md files with descriptions."""
    md_files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix == ".md" and f.name != "_index.md"
    )
    if not md_files:
        return

    try:
        rel_dir = str(directory.relative_to(root))
    except ValueError:
        rel_dir = str(directory)

    lines = [
        f"# {rel_dir}",
        "",
        "| File | Description |",
        "|------|-------------|",
    ]
    for f in md_files:
        desc = _read_frontmatter_field(f, "description") or ""
        lines.append(f"| [{f.name}]({f.name}) | {desc} |")

    index_path = directory / "_index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def discover_dirs(root: Path) -> list[Path]:
    """Return directories under root that contain non-index .md files."""
    dirs: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith(".") and d not in _SKIP
        )
        if any(f.endswith(".md") and f != "_index.md" for f in filenames):
            dirs.append(Path(dirpath))
    return dirs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create _index.md files and update AGENTS.md areas table.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    args = parser.parse_args()

    from wiki.agents_md import discover_areas, extract_areas, update_agents_md

    root = Path(args.root).resolve()

    # Create _index.md files in every directory with managed docs
    dirs = discover_dirs(root)
    for d in dirs:
        _write_index(d, root)

    # Update AGENTS.md areas table, preserving existing human descriptions
    agents_path = root / "AGENTS.md"
    if agents_path.is_file():
        content = agents_path.read_text(encoding="utf-8")
        existing = {a["path"]: a["name"] for a in extract_areas(content)}
        discovered = discover_areas(root)
        # Prefer existing description; fall back to path for new areas
        for area in discovered:
            if area["path"] in existing:
                area["name"] = existing[area["path"]]
        updated = update_agents_md(content, areas=discovered)
        agents_path.write_text(updated, encoding="utf-8")
        print(f"Updated {len(discovered)} area(s) in {agents_path}")
    else:
        print(f"AGENTS.md not found at {agents_path} — skipping areas update")

    print(f"Reindexed {len(dirs)} director{'y' if len(dirs) == 1 else 'ies'}")


if __name__ == "__main__":
    main()
