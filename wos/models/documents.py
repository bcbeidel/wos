"""Document model and type-specific subclasses.

BaseDocument is the renamed core Document. Each subclass overrides
``validate_structure()`` to compose the correct set of validators
for its document type — no dispatch table needed.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel

from wos.models.core import CitedSource, DocumentSection, DocumentType, ValidationIssue
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


class TopicDocument(BaseDocument):
    """A topic document with actionable guidance and citations."""

    @classmethod
    def from_template(
        cls,
        title: str,
        description: str,
        sources: List[CitedSource],
        *,
        area: Optional[str] = None,
        section_content: Optional[Dict[str, str]] = None,
    ) -> str:
        """Render a topic document with valid frontmatter and sections."""
        from wos.templates import render_topic

        return render_topic(
            title, description, sources,
            area=area, section_content=section_content,
        )

    def validate_structure(self) -> list[ValidationIssue]:
        from wos.validators import (
            check_go_deeper_links,
            check_last_validated,
            check_source_diversity,
        )

        issues = super().validate_structure()
        for validator in [
            check_last_validated,
            check_source_diversity,
            check_go_deeper_links,
        ]:
            issues.extend(validator(self))
        return issues

    def validate_content(self) -> list:
        from wos.tier2_triggers import (
            trigger_in_practice_concreteness,
            trigger_pitfalls_completeness,
        )

        results = super().validate_content()
        for trigger in [
            trigger_in_practice_concreteness,
            trigger_pitfalls_completeness,
        ]:
            results.extend(trigger(self))
        return results


class OverviewDocument(BaseDocument):
    """An overview document for area orientation and topic index."""

    @classmethod
    def from_template(
        cls,
        title: str,
        description: str,
        *,
        topics: Optional[List[str]] = None,
        section_content: Optional[Dict[str, str]] = None,
    ) -> str:
        """Render an overview document with valid frontmatter and sections."""
        from wos.templates import render_overview

        return render_overview(
            title, description,
            topics=topics, section_content=section_content,
        )

    def validate_structure(self) -> list[ValidationIssue]:
        from wos.validators import (
            check_last_validated,
            check_what_this_covers_length,
        )

        issues = super().validate_structure()
        for validator in [
            check_last_validated,
            check_what_this_covers_length,
        ]:
            issues.extend(validator(self))
        return issues

    def validate_content(self) -> list:
        from wos.tier2_triggers import trigger_overview_coverage_quality

        results = super().validate_content()
        results.extend(trigger_overview_coverage_quality(self))
        return results


class ResearchDocument(BaseDocument):
    """A research document capturing investigation findings."""

    @classmethod
    def from_template(
        cls,
        title: str,
        description: str,
        sources: List[CitedSource],
        *,
        section_content: Optional[Dict[str, str]] = None,
    ) -> str:
        """Render a research document with valid frontmatter and sections."""
        from wos.templates import render_research

        return render_research(
            title, description, sources,
            section_content=section_content,
        )

    def validate_structure(self) -> list[ValidationIssue]:
        from wos.validators import (
            check_date_prefix_matches,
            check_question_nonempty,
            check_source_diversity,
        )

        issues = super().validate_structure()
        for validator in [
            check_source_diversity,
            check_question_nonempty,
            check_date_prefix_matches,
        ]:
            issues.extend(validator(self))
        return issues

    def validate_content(self) -> list:
        from wos.tier2_triggers import (
            trigger_finding_groundedness,
            trigger_question_clarity,
        )

        results = super().validate_content()
        for trigger in [
            trigger_question_clarity,
            trigger_finding_groundedness,
        ]:
            results.extend(trigger(self))
        return results


class PlanDocument(BaseDocument):
    """A plan document with actionable work steps."""

    @classmethod
    def from_template(
        cls,
        title: str,
        description: str,
        *,
        section_content: Optional[Dict[str, str]] = None,
    ) -> str:
        """Render a plan document with valid frontmatter and sections."""
        from wos.templates import render_plan

        return render_plan(
            title, description,
            section_content=section_content,
        )

    def validate_structure(self) -> list[ValidationIssue]:
        from wos.validators import check_date_prefix_matches

        issues = super().validate_structure()
        issues.extend(check_date_prefix_matches(self))
        return issues

    def validate_content(self) -> list:
        from wos.tier2_triggers import (
            trigger_step_specificity,
            trigger_verification_completeness,
        )

        results = super().validate_content()
        for trigger in [
            trigger_step_specificity,
            trigger_verification_completeness,
        ]:
            results.extend(trigger(self))
        return results


class NoteDocument(BaseDocument):
    """A generic note document with minimal structure."""

    @classmethod
    def from_template(
        cls,
        title: str,
        description: str,
        *,
        body: str = "",
    ) -> str:
        """Render a note document — minimal frontmatter, free-form body."""
        from wos.templates import render_note

        return render_note(title, description, body=body)

    def validate_structure(self) -> list[ValidationIssue]:
        from wos.validators import check_title_heading

        issues: list[ValidationIssue] = []
        issues.extend(check_title_heading(self))
        return issues

    def validate_content(self) -> list:
        return []


# Backward compat alias — callers that import Document still work
Document = BaseDocument
