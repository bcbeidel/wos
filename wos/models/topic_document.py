"""TopicDocument — actionable guidance with citations."""

from __future__ import annotations

from typing import Dict, List, Optional

from wos.models.base_document import BaseDocument
from wos.models.core import CitedSource, IssueSeverity, ValidationIssue


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

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        from wos.validators import (
            check_go_deeper_links,
            check_last_validated,
            check_source_diversity,
        )

        issues = super().validate_self(deep=deep)
        for validator in [
            check_last_validated,
            check_source_diversity,
            check_go_deeper_links,
        ]:
            issues.extend(validator(self))
        return issues

    def validate_content(self) -> list[ValidationIssue]:
        issues = super().validate_content()

        # Check In Practice concreteness
        section = self.get_section_content("In Practice", "")
        if section:
            has_code = "```" in section or "    " in section
            has_list = "- " in section or "1. " in section
            if not has_code and not has_list:
                issues.append(
                    ValidationIssue(
                        file=self.path,
                        issue="In Practice section may lack concrete examples",
                        severity=IssueSeverity.INFO,
                        validator="validate_content",
                        section="In Practice",
                        suggestion="Add code blocks, bullet lists, or step-by-step examples",
                        requires_llm=True,
                    )
                )

        # Check Pitfalls completeness
        pitfalls = self.get_section_content("Pitfalls", "")
        if pitfalls and len(pitfalls.split()) < 20:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="Pitfalls section may be incomplete",
                    severity=IssueSeverity.INFO,
                    validator="validate_content",
                    section="Pitfalls",
                    suggestion="Add more common pitfalls and how to avoid them",
                    requires_llm=True,
                )
            )

        return issues
