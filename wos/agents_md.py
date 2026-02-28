"""AGENTS.md manager — marker-based WOS section rendering and updates.

Renders the WOS-managed section for AGENTS.md (context navigation,
areas table, file metadata format, preferences) and updates the file
content using marker-based replacement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

# ── Markers ──────────────────────────────────────────────────────

BEGIN_MARKER = "<!-- wos:begin -->"
END_MARKER = "<!-- wos:end -->"


# ── Discovery ────────────────────────────────────────────────────


def discover_areas(root: Path) -> List[Dict[str, str]]:
    """Discover areas by scanning docs/context/ subdirectories.

    Walks ``docs/context/`` under *root*, reads each subdirectory's
    ``_index.md`` preamble as the area description, and returns a
    sorted list of area dicts suitable for ``render_wos_section()``.

    Args:
        root: Project root directory.

    Returns:
        Sorted list of dicts with 'name' and 'path' keys.
    """
    from wos.index import _extract_preamble

    context_dir = root / "docs" / "context"
    if not context_dir.is_dir():
        return []

    areas: List[Dict[str, str]] = []
    for entry in sorted(context_dir.iterdir()):
        if not entry.is_dir():
            continue
        index_path = entry / "_index.md"
        preamble = _extract_preamble(index_path)
        name = preamble if preamble else entry.name
        rel_path = str(entry.relative_to(root))
        areas.append({"name": name, "path": rel_path})

    return areas


# ── Render ───────────────────────────────────────────────────────


def render_wos_section(
    areas: List[Dict[str, str]],
    preferences: Optional[List[str]] = None,
) -> str:
    """Render the WOS-managed section for AGENTS.md.

    Args:
        areas: List of dicts with 'name' and 'path' keys.
        preferences: Optional list of preference strings.

    Returns:
        Markdown string wrapped in begin/end markers.
    """
    lines: List[str] = [BEGIN_MARKER]

    # ── Context Navigation header ────────────────────────────────
    lines.append("## Context Navigation")
    lines.append("")
    lines.append(
        "Each directory has an `_index.md` listing all files with descriptions."
    )
    lines.append("- `docs/context/_index.md` -- all topic areas")
    lines.append("- `docs/plans/_index.md` -- plans")
    lines.append("- `docs/research/_index.md` -- research")
    lines.append("")
    lines.append(
        "Each `.md` file starts with YAML metadata (between `---` lines)."
    )
    lines.append(
        "Read the `description` field before reading the full file."
    )
    lines.append(
        "Documents put key insights first and last; supplemental detail in the middle."
    )

    # ── Areas table ──────────────────────────────────────────────
    if areas:
        lines.append("")
        lines.append("### Areas")
        lines.append("| Area | Path |")
        lines.append("|------|------|")
        for area in areas:
            lines.append(f"| {area['name']} | {area['path']} |")

    # ── File Metadata Format ─────────────────────────────────────
    lines.append("")
    lines.append("### File Metadata Format")
    lines.append("```yaml")
    lines.append("---")
    lines.append("name: Title")
    lines.append("description: What this covers")
    lines.append("type: research       # optional")
    lines.append("sources: []          # required if type is research")
    lines.append("related: []          # optional, file paths from project root")
    lines.append("---")
    lines.append("```")

    # ── Preferences ──────────────────────────────────────────────
    if preferences is not None and len(preferences) > 0:
        lines.append("")
        lines.append("### Preferences")
        for pref in preferences:
            lines.append(f"- {pref}")

    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


# ── Update ───────────────────────────────────────────────────────


def update_agents_md(
    content: str,
    areas: List[Dict[str, str]],
    preferences: Optional[List[str]] = None,
) -> str:
    """Replace or append the WOS section in AGENTS.md content.

    If markers exist, replaces the content between them (inclusive).
    If markers don't exist, appends the section to the end.
    Content outside markers is never touched.

    Args:
        content: The existing AGENTS.md content.
        areas: List of dicts with 'name' and 'path' keys.
        preferences: Optional list of preference strings.

    Returns:
        Updated AGENTS.md content with the new WOS section.
    """
    from wos.markers import replace_marker_section

    section = render_wos_section(areas, preferences)
    return replace_marker_section(content, BEGIN_MARKER, END_MARKER, section)
