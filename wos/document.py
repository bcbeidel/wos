"""Document dataclass and frontmatter parser.

Provides a single Document dataclass representing any WOS document
(topic, overview, research, plan) and a parse_document() function
that extracts YAML frontmatter into structured fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

# Known frontmatter fields extracted into Document attributes.
_KNOWN_FIELDS = {"name", "description", "type", "sources", "related"}


@dataclass
class Document:
    """A parsed WOS document with frontmatter metadata and body content."""

    path: str
    name: str
    description: str
    content: str
    type: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


def parse_document(path: str, text: str) -> Document:
    """Parse a markdown document with YAML frontmatter.

    Extracts frontmatter between ``---`` delimiters. Known fields
    (name, description, type, sources, related) become Document
    attributes; everything else goes into ``extra``.

    Args:
        path: File path for the document.
        text: Raw markdown text including frontmatter.

    Returns:
        A Document instance with parsed metadata and body content.

    Raises:
        ValueError: If frontmatter is missing, or required fields
            (name, description) are absent.
    """
    # ── Locate frontmatter delimiters ──────────────────────────
    if not text.startswith("---\n"):
        raise ValueError(
            f"{path}: no YAML frontmatter found "
            "(file must start with '---')"
        )

    # Find the closing delimiter (second '---').
    # Search for "\n---\n" first (normal case with content after).
    close_idx = text.find("\n---\n", 3)
    if close_idx != -1:
        yaml_end = close_idx
        content_start = close_idx + 5  # skip "\n---\n" (5 chars)
    else:
        # Try "\n---" at end of file (no trailing content)
        close_idx = text.find("\n---", 3)
        if close_idx != -1 and close_idx + 4 >= len(text):
            yaml_end = close_idx
            content_start = len(text)
        else:
            raise ValueError(
                f"{path}: no closing frontmatter delimiter found"
            )

    # ── Parse YAML ─────────────────────────────────────────────
    yaml_text = text[4:yaml_end]  # skip opening "---\n"
    fm = yaml.safe_load(yaml_text)

    if not isinstance(fm, dict):
        # empty or non-mapping frontmatter
        fm = {}

    # ── Validate required fields ───────────────────────────────
    if "name" not in fm:
        raise ValueError(f"{path}: frontmatter missing required field 'name'")
    if "description" not in fm:
        raise ValueError(
            f"{path}: frontmatter missing required field 'description'"
        )

    # ── Extract known fields ───────────────────────────────────
    name: str = fm["name"]
    description: str = fm["description"]
    doc_type: Optional[str] = fm.get("type")
    sources: List[str] = fm.get("sources", [])
    related: List[str] = fm.get("related", [])

    # Everything else goes into extra
    extra: Dict[str, Any] = {
        k: v for k, v in fm.items() if k not in _KNOWN_FIELDS
    }

    # ── Extract body content ───────────────────────────────────
    content = text[content_start:] if content_start < len(text) else ""

    return Document(
        path=path,
        name=name,
        description=description,
        content=content,
        type=doc_type,
        sources=sources,
        related=related,
        extra=extra,
    )
