"""BaseDocument — the core parsed document model."""

from __future__ import annotations

import re
from typing import Iterator, List, Optional

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

    # ── String representations ─────────────────────────────────────

    def __str__(self) -> str:
        return f"{self.title} ({self.document_type.value})"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(path={self.path!r}, "
            f"type={self.document_type.value!r})"
        )

    # ── Collection protocol ────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.sections)

    def __iter__(self) -> Iterator[DocumentSection]:  # type: ignore[override]
        return iter(self.sections)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return item in self.section_names
        if isinstance(item, DocumentSection):
            return item in self.sections
        return False

    # ── Properties ─────────────────────────────────────────────────

    @property
    def area_name(self) -> Optional[str]:
        """Extract area name from context path. Returns None for non-context docs."""
        m = re.match(r"context/([^/]+)/", self.path)
        return m.group(1) if m else None

    # ── Construction ───────────────────────────────────────────────

    @classmethod
    def from_markdown(cls, path: str, content: str) -> BaseDocument:
        """Parse markdown content into a document."""
        from wos.models.parsing import parse_document

        return parse_document(path, content)

    @classmethod
    def from_json(cls, data: dict) -> BaseDocument:
        """Reconstruct a document from to_json() output.

        Requires raw_content to be present for re-parsing.
        """
        raw = data.get("raw_content", "")
        if raw:
            from wos.models.parsing import parse_document

            return parse_document(data["path"], raw)
        raise ValueError("Cannot reconstruct document without raw_content")

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

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return {
            "path": self.path,
            "document_type": self.document_type.value,
            "title": self.title,
            "frontmatter": self.frontmatter.model_dump(mode="json"),
            "sections": [s.to_json() for s in self.sections],
            "raw_content": self.raw_content,
        }

    def to_markdown(self) -> str:
        """Render full document with YAML frontmatter + title + sections.

        The document knows how to serialize itself. Output should be
        re-parseable by parse_document().
        """
        fm_data = self.frontmatter.model_dump(mode="json", exclude_none=True)

        # Build frontmatter YAML manually for deterministic output
        lines = ["---"]

        # document_type first
        lines.append(f"document_type: {fm_data.pop('document_type')}")

        # description second (escaped for YAML)
        desc = fm_data.pop("description")
        lines.append(f'description: "{_escape_yaml(desc)}"')

        # Render remaining fields in a stable order
        for key in sorted(fm_data.keys()):
            value = fm_data[key]
            if key == "sources" and isinstance(value, list):
                lines.append("sources:")
                for src in value:
                    lines.append(f'  - url: "{src["url"]}"')
                    lines.append(f'    title: "{_escape_yaml(src["title"])}"')
            elif isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")

        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")

        for s in self.sections:
            lines.append("")
            lines.append(f"## {s.name}")
            lines.append("")
            lines.append(s.content)

        lines.append("")
        return "\n".join(lines)

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

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        """Run structural validators for this document type.

        Subclasses override to add type-specific validators via
        ``super().validate_self()``. The ``deep`` parameter is accepted
        for protocol consistency but not yet used at the base level.
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

    @property
    def is_valid(self) -> bool:
        """True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0

    def validate_content(self) -> list:
        """Run Tier 2 content triggers for LLM-assisted quality assessment.

        Returns list of TriggerContext dicts. Subclasses override to add
        type-specific triggers.
        """
        from wos.tier2_triggers import trigger_description_quality

        results: list = []
        results.extend(trigger_description_quality(self))
        return results


def _escape_yaml(s: str) -> str:
    """Escape characters that would break YAML double-quoted strings."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


# Backward compat alias — callers that import Document still work
Document = BaseDocument
