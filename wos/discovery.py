"""Discovery layer — scan context documents and generate manifests.

Scans a project's /context/ directory, reads frontmatter from context
documents (topics + overviews), and generates:
  - CLAUDE.md manifest section (markdown between markers under ## Context)
  - .claude/rules/work-os-context.md (compact behavioral guide)
  - AGENTS.md (mirrors the CLAUDE.md manifest)

All outputs are deterministic — running twice produces identical results.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from wos.document_types import DocumentType, parse_document

# ── Markers ──────────────────────────────────────────────────────

MARKER_BEGIN = "<!-- work-os:context:begin -->"
MARKER_END = "<!-- work-os:context:end -->"


# ── Data structures ──────────────────────────────────────────────


@dataclass
class TopicInfo:
    """Metadata for a single topic document."""

    path: str  # root-relative, e.g. "context/python/error-handling.md"
    title: str
    description: str


@dataclass
class AreaInfo:
    """Metadata for a context area (directory under /context/)."""

    name: str  # directory name, e.g. "python"
    display_name: str  # title-cased for headings, e.g. "Python"
    overview_path: Optional[str]  # root-relative path to _overview.md
    overview_description: Optional[str]
    topics: List[TopicInfo] = field(default_factory=list)


# ── Step 1: Scan ─────────────────────────────────────────────────


def scan_context(root: str) -> List[AreaInfo]:
    """Walk /context/ and return structured metadata for each area.

    Skips files that fail to parse. Areas are sorted alphabetically.
    Topics within each area are sorted alphabetically by filename.
    """
    context_dir = Path(root) / "context"
    if not context_dir.is_dir():
        return []

    areas: List[AreaInfo] = []

    for entry in sorted(context_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        area = AreaInfo(
            name=entry.name,
            display_name=_display_name(entry.name),
            overview_path=None,
            overview_description=None,
        )

        for md_file in sorted(entry.iterdir()):
            if not md_file.is_file() or md_file.suffix != ".md":
                continue

            rel_path = str(md_file.relative_to(root))
            try:
                content = md_file.read_text(encoding="utf-8")
                doc = parse_document(rel_path, content)
            except Exception:
                continue

            if doc.document_type == DocumentType.OVERVIEW:
                area.overview_path = rel_path
                area.overview_description = doc.frontmatter.description
            elif doc.document_type == DocumentType.TOPIC:
                area.topics.append(
                    TopicInfo(
                        path=rel_path,
                        title=doc.title or _display_name(md_file.stem),
                        description=doc.frontmatter.description,
                    )
                )

        areas.append(area)

    return areas


def _display_name(slug: str) -> str:
    """Convert a hyphenated slug to a display name.

    'python-basics' -> 'Python Basics'
    """
    return slug.replace("-", " ").title()


# ── Step 2: Render manifest ─────────────────────────────────────


def render_manifest(areas: List[AreaInfo]) -> str:
    """Generate a compact markdown manifest from scanned areas.

    Produces a single area-level table. Each area links to its _overview.md
    (or directory if no overview exists). Topic details are deferred to the
    overview files — progressive disclosure keeps the manifest small.

    Returns the content to place between markers (not including markers).
    """
    if not areas:
        return ""

    parts: List[str] = [
        "| Area | Description |",
        "|------|-------------|",
    ]

    for area in areas:
        description = area.overview_description or ""
        if area.overview_path:
            link = f"[{area.display_name}]({area.overview_path})"
        else:
            link = f"[{area.display_name}](context/{area.name}/)"
        parts.append(f"| {link} | {description} |")

    return "\n".join(parts)


# ── Step 3: Update CLAUDE.md ────────────────────────────────────


def update_claude_md(file_path: str, manifest_content: str) -> None:
    """Update CLAUDE.md with the manifest between markers.

    If markers exist, replaces content between them.
    If no markers exist, appends a ## Context section with markers.
    If the file doesn't exist, creates it with a best-practices template.
    """
    path = Path(file_path)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if MARKER_BEGIN not in existing:
            print(
                f"  CLAUDE.md exists without markers — appending ## Context "
                f"section ({len(existing.splitlines())} existing lines preserved)",
                file=sys.stderr,
            )
    else:
        existing = _claude_md_template()
        print(
            "  CLAUDE.md not found — creating from template",
            file=sys.stderr,
        )

    updated = _replace_between_markers(existing, manifest_content)
    path.write_text(updated, encoding="utf-8")


def _claude_md_template() -> str:
    """Best-practices CLAUDE.md template for new projects."""
    return (
        "# CLAUDE.md\n"
        "\n"
        "## Build & Test\n"
        "\n"
        "<!-- Add build and test commands here -->\n"
        "\n"
        "## Context\n"
        "\n"
        f"{MARKER_BEGIN}\n"
        f"{MARKER_END}\n"
    )


def _replace_between_markers(content: str, manifest: str) -> str:
    """Replace content between markers, or add markers if missing."""
    begin_idx = content.find(MARKER_BEGIN)
    end_idx = content.find(MARKER_END)

    if begin_idx != -1 and end_idx != -1:
        # Replace between markers
        before = content[: begin_idx + len(MARKER_BEGIN)]
        after = content[end_idx:]
        if manifest:
            return f"{before}\n{manifest}\n{after}"
        return f"{before}\n{after}"

    # No markers found — append ## Context section
    section = (
        "\n## Context\n"
        "\n"
        f"{MARKER_BEGIN}\n"
    )
    if manifest:
        section += f"{manifest}\n"
    section += f"{MARKER_END}\n"

    return content.rstrip("\n") + "\n" + section


# ── Step 4: Render rules file ───────────────────────────────────


def render_rules_file() -> str:
    """Generate a compact behavioral guide for agents.

    Under 50 lines, actionable only. Describes document types, directories,
    frontmatter requirements, and pointers to /wos: skills.
    """
    return """\
# Work-OS Context Rules

## Document Types

| Type | Directory | Purpose |
|------|-----------|---------|
| topic | `context/{area}/{slug}.md` | Actionable guidance with citations |
| overview | `context/{area}/_overview.md` | Area orientation and topic index |
| research | `artifacts/research/{date}-{slug}.md` | Investigation snapshot |
| plan | `artifacts/plans/{date}-{slug}.md` | Actionable work plan |

## Frontmatter Requirements

All documents require YAML frontmatter with `document_type`, `description`,
and `last_updated`. Additional requirements by type:

- **topic**: `sources` (list of url+title), `last_validated` (date)
- **overview**: `last_validated` (date)
- **research**: `sources` (list of url+title)
- **plan**: `status` (draft|active|complete|abandoned)

Optional on all types: `tags` (lowercase-hyphenated), `related` (file paths or URLs).

## Agent Guidelines

- Context types (topic, overview) appear in the CLAUDE.md manifest
- Artifact types (research, plan) are internal — reachable via `related` links
- Use `/wos:curate` to create or update documents
- Use `/wos:health` to check document validity
- Use `/wos:maintain` to fix issues found by health
- `related` uses root-relative file paths (e.g., `context/python/error-handling.md`)
- Never edit content between work-os markers manually — auto-generated by discovery
"""


# ── Step 5: Update rules file ───────────────────────────────────


def update_rules_file(root: str, content: str) -> None:
    """Write the rules file, creating the directory if needed."""
    rules_path = Path(root) / ".claude" / "rules" / "work-os-context.md"
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(content, encoding="utf-8")


# ── Step 7: Update AGENTS.md ────────────────────────────────────


def update_agents_md(file_path: str, manifest_content: str) -> None:
    """Update AGENTS.md with the same manifest between markers.

    Same marker logic as CLAUDE.md. Creates the file if it doesn't exist.
    """
    path = Path(file_path)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
    else:
        existing = _agents_md_template()
        print(
            "  AGENTS.md not found — creating from template",
            file=sys.stderr,
        )

    updated = _replace_between_markers(existing, manifest_content)
    path.write_text(updated, encoding="utf-8")


def _agents_md_template() -> str:
    """AGENTS.md template for new projects."""
    return (
        "# AGENTS.md\n"
        "\n"
        "## Context\n"
        "\n"
        f"{MARKER_BEGIN}\n"
        f"{MARKER_END}\n"
    )


# ── Orchestration ────────────────────────────────────────────────


def run_discovery(root: str) -> None:
    """Full discovery pipeline: scan → render → update all files."""
    root = os.path.abspath(root)

    print(f"Discovery root: {root}", file=sys.stderr)

    areas = scan_context(root)
    print(f"Found {len(areas)} context area(s)", file=sys.stderr)

    manifest = render_manifest(areas)

    update_claude_md(os.path.join(root, "CLAUDE.md"), manifest)
    update_agents_md(os.path.join(root, "AGENTS.md"), manifest)

    rules = render_rules_file()
    update_rules_file(root, rules)
