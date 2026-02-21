"""PlanDocument — actionable work plan."""

from __future__ import annotations

from typing import Dict, Optional

from wos.models.base_document import BaseDocument
from wos.models.validation_issue import ValidationIssue


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
