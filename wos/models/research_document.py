"""ResearchDocument — investigation snapshot."""

from __future__ import annotations

from typing import Dict, List, Optional

from wos.models.base_document import BaseDocument
from wos.models.cited_source import CitedSource
from wos.models.validation_issue import ValidationIssue


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
