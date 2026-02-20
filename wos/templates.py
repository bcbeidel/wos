"""Document templates — render valid markdown for each document type.

Each render function produces a complete markdown document with correct
YAML frontmatter and section headings derived from the SECTIONS dispatch
table. Output passes parse_document() validation.

Dispatch is handled by each document subclass's from_template() classmethod.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from wos.document_types import SECTIONS, DocumentType, Source


def render_topic(
    title: str,
    description: str,
    sources: List[Source],
    *,
    area: Optional[str] = None,
    section_content: Optional[Dict[str, str]] = None,
) -> str:
    """Render a topic document with valid frontmatter and sections."""
    today = date.today().isoformat()
    content = section_content or {}

    sources_yaml = _render_sources_yaml(sources)
    sections = _render_sections(DocumentType.TOPIC, content)

    return (
        "---\n"
        "document_type: topic\n"
        f'description: "{_escape_yaml(description)}"\n'
        f"last_updated: {today}\n"
        f"last_validated: {today}\n"
        f"sources:\n{sources_yaml}"
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        f"{sections}"
    )


def render_overview(
    title: str,
    description: str,
    *,
    topics: Optional[List[str]] = None,
    section_content: Optional[Dict[str, str]] = None,
) -> str:
    """Render an overview document with valid frontmatter and sections."""
    today = date.today().isoformat()
    content = section_content or {}

    # Provide sensible defaults for key sections
    if "What This Covers" not in content:
        content["What This Covers"] = (
            f"This area covers {description.lower()}. "
            "It provides guidance on key concepts, common patterns, "
            "and best practices for the topics listed below. "
            "Both human developers and AI agents will find "
            "actionable information organized by topic."
        )
    if "Topics" not in content:
        if topics:
            content["Topics"] = "\n".join(f"- {t}" for t in topics)
        else:
            content["Topics"] = (
                "<!-- Topics will be listed here as they are added -->"
            )
    if "Key Sources" not in content:
        content["Key Sources"] = (
            "<!-- Add authoritative sources for this area -->"
        )

    sections = _render_sections(DocumentType.OVERVIEW, content)

    return (
        "---\n"
        "document_type: overview\n"
        f'description: "{_escape_yaml(description)}"\n'
        f"last_updated: {today}\n"
        f"last_validated: {today}\n"
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        f"{sections}"
    )


def render_research(
    title: str,
    description: str,
    sources: List[Source],
    *,
    section_content: Optional[Dict[str, str]] = None,
) -> str:
    """Render a research document with valid frontmatter and sections."""
    today = date.today().isoformat()
    content = section_content or {}

    sources_yaml = _render_sources_yaml(sources)
    sections = _render_sections(DocumentType.RESEARCH, content)

    return (
        "---\n"
        "document_type: research\n"
        f'description: "{_escape_yaml(description)}"\n'
        f"last_updated: {today}\n"
        f"sources:\n{sources_yaml}"
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        f"{sections}"
    )


def render_plan(
    title: str,
    description: str,
    *,
    section_content: Optional[Dict[str, str]] = None,
) -> str:
    """Render a plan document with valid frontmatter and sections."""
    today = date.today().isoformat()
    content = section_content or {}

    sections = _render_sections(DocumentType.PLAN, content)

    return (
        "---\n"
        "document_type: plan\n"
        f'description: "{_escape_yaml(description)}"\n'
        f"last_updated: {today}\n"
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        f"{sections}"
    )


def render_note(
    title: str,
    description: str,
    *,
    body: str = "",
) -> str:
    """Render a note document — minimal frontmatter, free-form body."""
    return (
        "---\n"
        "document_type: note\n"
        f'description: "{_escape_yaml(description)}"\n'
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        f"{body or '<!-- Add content -->'}\n"
    )


# ── Helpers ──────────────────────────────────────────────────────


def _render_sections(
    doc_type: DocumentType,
    content: Dict[str, str],
) -> str:
    """Render sections from the SECTIONS dispatch table."""
    specs = SECTIONS[doc_type]
    parts: List[str] = []

    for spec in specs:
        heading = f"## {spec.name}"
        body = content.get(spec.name, "")
        if not body:
            body = f"<!-- Add {spec.name.lower()} content -->"
        parts.append(f"{heading}\n\n{body}")

    return "\n\n".join(parts) + "\n"


def _render_sources_yaml(sources: List[Source]) -> str:
    """Render sources as YAML list items."""
    lines: List[str] = []
    for source in sources:
        lines.append(f'  - url: "{source.url}"')
        lines.append(f'    title: "{_escape_yaml(source.title)}"')
    return "\n".join(lines) + "\n"


def _escape_yaml(s: str) -> str:
    """Escape characters that would break YAML double-quoted strings."""
    return s.replace("\\", "\\\\").replace('"', '\\"')
