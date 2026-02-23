"""Index generator for directory-level _index.md files.

Provides generate_index() to create _index.md content from directory
contents and frontmatter, and check_index_sync() to verify an existing
_index.md is up to date.

This module is intentionally independent of wos.document — it uses
yaml.safe_load directly so it can be used without the full document
parsing pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml


def _extract_description(file_path: Path) -> Optional[str]:
    """Extract description from YAML frontmatter of a markdown file.

    Args:
        file_path: Path to a .md file.

    Returns:
        The description string, or None if no frontmatter or no
        description field is present.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not text.startswith("---\n"):
        return None

    close_idx = text.find("\n---\n", 3)
    if close_idx == -1:
        close_idx = text.find("\n---", 3)
        if close_idx == -1 or close_idx + 4 < len(text):
            return None

    yaml_text = text[4:close_idx]
    try:
        fm = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None

    if not isinstance(fm, dict):
        return None

    desc = fm.get("description")
    if desc is None:
        return None

    return str(desc)


def _directory_display_name(directory: Path) -> str:
    """Convert a directory name to a display name.

    Replaces hyphens and underscores with spaces and applies title case.
    """
    return directory.name.replace("-", " ").replace("_", " ").title()


def generate_index(directory: Path) -> str:
    """Generate _index.md content for a directory.

    Lists all .md files (except _index.md) with descriptions extracted
    from their YAML frontmatter, and all subdirectories with descriptions
    from their _index.md files.

    Args:
        directory: Path to the directory to index.

    Returns:
        Markdown string suitable for writing to _index.md.
    """
    heading = _directory_display_name(directory)
    lines: List[str] = [f"# {heading}\n"]

    # ── Collect .md files (excluding _index.md) ────────────────
    md_files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix == ".md" and f.name != "_index.md"
    )

    # ── Collect subdirectories ─────────────────────────────────
    subdirs = sorted(
        d for d in directory.iterdir()
        if d.is_dir()
    )

    # ── File table ─────────────────────────────────────────────
    if md_files:
        lines.append("")
        lines.append("| File | Description |")
        lines.append("| --- | --- |")
        for f in md_files:
            desc = _extract_description(f)
            desc_text = desc if desc is not None else "*(no description)*"
            lines.append(f"| [{f.name}]({f.name}) | {desc_text} |")

    # ── Subdirectory table ─────────────────────────────────────
    if subdirs:
        lines.append("")
        lines.append("| Directory | Description |")
        lines.append("| --- | --- |")
        for d in subdirs:
            sub_index = d / "_index.md"
            desc = _extract_description(sub_index) if sub_index.is_file() else None
            desc_text = desc if desc is not None else _directory_display_name(d)
            lines.append(f"| [{d.name}/]({d.name}/) | {desc_text} |")

    lines.append("")
    return "\n".join(lines)


def check_index_sync(directory: Path) -> List[dict]:
    """Check if _index.md matches the current directory contents.

    Args:
        directory: Path to the directory to check.

    Returns:
        A list of issue dicts. Empty if _index.md is in sync.
        Each dict has keys: file, issue, severity (always "fail").
    """
    index_path = directory / "_index.md"

    if not index_path.is_file():
        return [
            {
                "file": str(index_path),
                "issue": "_index.md is missing",
                "severity": "fail",
            }
        ]

    # Compare current generated content with what's on disk
    current_content = generate_index(directory)
    existing_content = index_path.read_text(encoding="utf-8")

    if current_content != existing_content:
        return [
            {
                "file": str(index_path),
                "issue": "_index.md is out of sync with directory contents",
                "severity": "fail",
            }
        ]

    return []
