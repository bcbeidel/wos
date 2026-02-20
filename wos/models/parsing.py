"""Markdown parsing: frontmatter extraction, section splitting, document construction."""

from __future__ import annotations

import re

import yaml
from pydantic import TypeAdapter, ValidationError

from wos.models.core import DocumentSection, DocumentType
from wos.models.documents import (
    BaseDocument,
    NoteDocument,
    OverviewDocument,
    PlanDocument,
    ResearchDocument,
    TopicDocument,
)
from wos.models.frontmatter import Frontmatter

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

_SUBCLASS_BY_TYPE = {
    DocumentType.TOPIC: TopicDocument,
    DocumentType.OVERVIEW: OverviewDocument,
    DocumentType.RESEARCH: ResearchDocument,
    DocumentType.PLAN: PlanDocument,
    DocumentType.NOTE: NoteDocument,
}


def _split_markdown(
    content: str,
) -> tuple[dict, str, list[DocumentSection], str]:
    """Parse YAML frontmatter, title, and sections from markdown.

    Returns (frontmatter_dict, title, sections, raw_content).

    Raises ValidationError if no YAML frontmatter is found.
    Sections are keyed by H2 heading name; H3+ headings are content
    within their parent H2 section.
    """
    fm_match = _FRONTMATTER_RE.match(content)
    if not fm_match:
        raise ValidationError.from_exception_data(
            title="Document",
            line_errors=[
                {
                    "type": "value_error",
                    "loc": ("frontmatter",),
                    "msg": "No YAML frontmatter found (expected --- delimiters)",
                    "input": content[:100],
                    "ctx": {"error": ValueError("No YAML frontmatter found")},
                }
            ],
        )

    frontmatter_yaml = fm_match.group(1)
    frontmatter_dict = yaml.safe_load(frontmatter_yaml) or {}

    body = content[fm_match.end() :]

    # Extract title from first H1
    h1_match = _H1_RE.search(body)
    title = h1_match.group(1).strip() if h1_match else ""

    # Extract sections by H2 headings
    sections: list[DocumentSection] = []
    h2_matches = list(_H2_RE.finditer(body))
    for i, m in enumerate(h2_matches):
        section_name = m.group(1).strip()
        start = m.end()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(body)
        sections.append(
            DocumentSection(name=section_name, content=body[start:end].strip())
        )

    return frontmatter_dict, title, sections, content


def parse_document(path: str, content: str) -> BaseDocument:
    """Parse a markdown file into a validated Document.

    Returns the appropriate subclass (TopicDocument, OverviewDocument, etc.)
    based on the document_type frontmatter field.

    Raises ValidationError with clear messages on:
    - Missing or invalid YAML frontmatter
    - Missing or invalid frontmatter fields
    - Wrong document_type value
    - Invalid dates, empty sources, bad status values
    - Type-specific field violations
    """
    frontmatter_dict, title, sections, raw = _split_markdown(content)

    # Validate frontmatter via discriminated union
    adapter = TypeAdapter(Frontmatter)
    frontmatter = adapter.validate_python(frontmatter_dict)

    # Determine the correct subclass
    doc_type = DocumentType(frontmatter.document_type)
    cls = _SUBCLASS_BY_TYPE.get(doc_type, BaseDocument)

    return cls(
        path=path,
        frontmatter=frontmatter,
        title=title,
        sections=sections,
        raw_content=raw,
    )
