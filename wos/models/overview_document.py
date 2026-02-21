"""OverviewDocument — area orientation and topic index."""

from __future__ import annotations

from typing import Dict, List, Optional

from wos.models.base_document import BaseDocument
from wos.models.validation_issue import ValidationIssue


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

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        from wos.validators import (
            check_last_validated,
            check_what_this_covers_length,
        )

        issues = super().validate_self(deep=deep)
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
