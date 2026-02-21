"""BaseDocument — the core parsed document model."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from wos.models.enums import DocumentType
from wos.models.section import DocumentSection
from wos.models.validation_issue import ValidationIssue
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
    frontmatter_line_end: Optional[int] = None
    title_line: Optional[int] = None

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

    # ── Representations ────────────────────────────────────────────

    def to_index_record(self) -> dict:
        """Compact record for scanning/indexing (path, type, title, description)."""
        return {
            "path": self.path,
            "document_type": self.document_type.value,
            "title": self.title,
            "description": self.frontmatter.description,
        }

    def to_outline(self) -> str:
        """Section headings with word counts — for quick orientation."""
        lines = [f"# {self.title} ({self.document_type.value})"]
        for s in self.sections:
            lines.append(f"## {s.name} ({s.word_count} words)")
        return "\n".join(lines)

    def to_plain_text(self) -> str:
        """Full plain-text rendering (title + sections, no frontmatter)."""
        parts = [f"# {self.title}"]
        for s in self.sections:
            parts.append(f"## {s.name}\n\n{s.content}")
        return "\n\n".join(parts)

    def get_estimated_tokens(self) -> int:
        """Estimate total token cost of this document."""
        # Title
        tokens = len(self.title) // 4 + 2
        # Frontmatter (description + metadata)
        tokens += len(self.frontmatter.description) // 4 + 10
        # Sections
        for s in self.sections:
            tokens += len(s.name) // 4 + 2  # heading
            tokens += len(s.content) // 4  # content
        return tokens

    # ── Validation ──────────────────────────────────────────────

    def validate_structure(self) -> list[ValidationIssue]:
        """Run structural validators for this document type.

        Subclasses override to add type-specific validators.
        """
        from wos.validators import (
            check_date_fields,
            check_directory_placement,
            check_heading_hierarchy,
            check_placeholder_comments,
            check_section_ordering,
            check_section_presence,
            check_size_bounds,
            check_title_heading,
        )

        issues: list[ValidationIssue] = []
        for validator in [
            check_section_presence,
            check_section_ordering,
            check_size_bounds,
            check_directory_placement,
            check_title_heading,
            check_heading_hierarchy,
            check_placeholder_comments,
            check_date_fields,
        ]:
            issues.extend(validator(self))
        return issues

    def validate_content(self) -> list:
        """Run Tier 2 content triggers for LLM-assisted quality assessment.

        Returns list of TriggerContext dicts. Subclasses override to add
        type-specific triggers.
        """
        from wos.tier2_triggers import trigger_description_quality

        results: list = []
        results.extend(trigger_description_quality(self))
        return results


# Backward compat alias — callers that import Document still work
Document = BaseDocument
