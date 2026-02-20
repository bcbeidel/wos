"""Discovery layer — scan context documents and generate manifests.

Scans a project's /context/ directory, reads frontmatter from context
documents (topics + overviews), and generates:
  - CLAUDE.md manifest section (markdown between markers under ## Context)
  - .claude/rules/wos-context.md (compact behavioral guide)
  - AGENTS.md (mirrors the CLAUDE.md manifest)

All outputs are deterministic — running twice produces identical results.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

from wos.models.context_area import ContextArea

# ── Markers ──────────────────────────────────────────────────────

MARKER_BEGIN = "<!-- wos:context:begin -->"
MARKER_END = "<!-- wos:context:end -->"


# ── Step 1: Scan ─────────────────────────────────────────────────


def scan_context(root: str) -> List[ContextArea]:
    """Walk /context/ and return ContextArea for each area directory.

    Delegates to ContextArea.scan_all(). Skips files that fail to parse.
    Areas are sorted alphabetically.
    """
    return ContextArea.scan_all(root)


# ── Step 2: Render manifest ─────────────────────────────────────


def render_manifest(areas: List[ContextArea]) -> str:
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
        parts.append(area.to_manifest_entry())

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
# WOS Context Rules

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
- Never edit content between wos markers manually — auto-generated by discovery
"""


# ── Step 5: Update rules file ───────────────────────────────────


def update_rules_file(root: str, content: str) -> None:
    """Write the rules file, creating the directory if needed."""
    rules_path = Path(root) / ".claude" / "rules" / "wos-context.md"
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
