"""TopicDocument — actionable guidance with citations."""

from __future__ import annotations

from typing import Dict, List, Optional

from wos.models.base_document import BaseDocument
from wos.models.cited_source import CitedSource
from wos.models.validation_issue import ValidationIssue


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
