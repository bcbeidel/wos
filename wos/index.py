"""Index generator for directory-level _index.md files.

Provides generate_index() to create _index.md content from directory
contents and frontmatter, and check_index_sync() to verify an existing
_index.md is up to date.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from wos.document import parse_document


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

    try:
        doc = parse_document(str(file_path), text)
    except ValueError:
        return None

    return doc.description if doc.description else None


def _directory_display_name(directory: Path) -> str:
    """Convert a directory name to a display name.

    Replaces hyphens and underscores with spaces and applies title case.
    """
    return directory.name.replace("-", " ").replace("_", " ").title()


def _extract_preamble(index_path: Path) -> Optional[str]:
    """Extract preamble text from an existing _index.md.

    The preamble is any text between the heading line and the first
    table line (starting with '|'). Returns None if no preamble
    exists or the file is missing.
    """
    if not index_path.is_file():
        return None

    try:
        content = index_path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = content.splitlines()
    heading_idx = None
    table_idx = None

    for i, line in enumerate(lines):
        if heading_idx is None and line.startswith("# "):
            heading_idx = i
        elif heading_idx is not None and line.startswith("|"):
            table_idx = i
            break

    if heading_idx is None or table_idx is None:
        return None

    # Extract lines between heading and table, strip blanks
    preamble_lines = [
        l for l in lines[heading_idx + 1:table_idx] if l.strip()
    ]
    if not preamble_lines:
        return None

    return "\n".join(preamble_lines)


def generate_index(directory: Path, preamble: Optional[str] = None) -> str:
    """Generate _index.md content for a directory.

    Lists all .md files (except _index.md) with descriptions extracted
    from their YAML frontmatter, and all subdirectories with descriptions
    from their _index.md files.

    Args:
        directory: Path to the directory to index.
        preamble: Optional area description text to insert between
            the heading and the file table.

    Returns:
        Markdown string suitable for writing to _index.md.
    """
    heading = _directory_display_name(directory)
    lines: List[str] = [f"# {heading}\n"]

    if preamble:
        lines.append("")
        lines.append(preamble)

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

    # Preserve preamble when comparing
    preamble = _extract_preamble(index_path)
    current_content = generate_index(directory, preamble=preamble)
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
