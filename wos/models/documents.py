"""Document model and type-specific subclasses.

BaseDocument is the renamed core Document. Type-specific subclasses
(TopicDocument, etc.) will gain behavior in later steps as validators,
templates, and triggers are migrated onto them.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from wos.models.core import DocumentSection, DocumentType
from wos.models.frontmatter import (
    SECTIONS,
    SIZE_BOUNDS,
    Frontmatter,
    SectionSpec,
    SizeBounds,
)


class BaseDocument(BaseModel):
    """A complete parsed knowledge record."""

    path: str
    frontmatter: Frontmatter  # discriminated union dispatches here
    title: str
    sections: List[DocumentSection]
    raw_content: str

    @property
    def document_type(self) -> DocumentType:
        return DocumentType(self.frontmatter.document_type)

    @property
    def required_sections(self) -> list[SectionSpec]:
        return SECTIONS[self.document_type]

    @property
    def size_bounds(self) -> SizeBounds:
        return SIZE_BOUNDS[self.document_type]

    @property
    def section_names(self) -> list[str]:
        """Ordered list of section names."""
        return [s.name for s in self.sections]

    def get_section(self, name: str) -> Optional[DocumentSection]:
        """Get a section by name, or None if not found."""
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def get_section_content(self, name: str, default: str = "") -> str:
        """Get section content by name, or default if not found."""
        s = self.get_section(name)
        return s.content if s else default

    def has_section(self, name: str) -> bool:
        """Check if a section exists by name."""
        return any(s.name == name for s in self.sections)


class TopicDocument(BaseDocument):
    """A topic document with actionable guidance and citations."""

    pass


class OverviewDocument(BaseDocument):
    """An overview document for area orientation and topic index."""

    pass


class ResearchDocument(BaseDocument):
    """A research document capturing investigation findings."""

    pass


class PlanDocument(BaseDocument):
    """A plan document with actionable work steps."""

    pass


class NoteDocument(BaseDocument):
    """A generic note document with minimal structure."""

    pass


# Backward compat alias — callers that import Document still work
Document = BaseDocument
