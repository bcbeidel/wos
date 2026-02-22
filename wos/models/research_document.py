"""ResearchDocument — investigation snapshot."""

from __future__ import annotations

from typing import Dict, List, Optional

from wos.models.base_document import BaseDocument
from wos.models.core import CitedSource, IssueSeverity, ValidationIssue


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

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        from wos.validators import (
            check_date_prefix_matches,
            check_question_nonempty,
            check_source_diversity,
        )

        issues = super().validate_self(deep=deep)
        for validator in [
            check_source_diversity,
            check_question_nonempty,
            check_date_prefix_matches,
        ]:
            issues.extend(validator(self))
        return issues

    def validate_content(self) -> list[ValidationIssue]:
        issues = super().validate_content()

        # Check question clarity
        question = self.get_section_content("Question", "")
        if question and "?" not in question:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="Research question may not be clearly framed as a question",
                    severity=IssueSeverity.INFO,
                    validator="validate_content",
                    section="Question",
                    suggestion="Frame as a specific, answerable question",
                    requires_llm=True,
                )
            )

        # Check finding groundedness
        findings = self.get_section_content("Findings", "")
        has_links = "[" in findings and "](" in findings
        if findings and not has_links and len(findings.split()) > 50:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="Findings may not be well-grounded in sources",
                    severity=IssueSeverity.INFO,
                    validator="validate_content",
                    section="Findings",
                    suggestion="Add citations or links to supporting sources",
                    requires_llm=True,
                )
            )

        return issues
