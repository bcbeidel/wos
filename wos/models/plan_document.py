"""PlanDocument — actionable work plan."""

from __future__ import annotations

from typing import Dict, Optional

from wos.models.base_document import BaseDocument
from wos.models.core import IssueSeverity, ValidationIssue


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

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        from wos.validators import check_date_prefix_matches

        issues = super().validate_self(deep=deep)
        issues.extend(check_date_prefix_matches(self))
        return issues

    def validate_content(self) -> list[ValidationIssue]:
        issues = super().validate_content()

        # Check step specificity
        steps = self.get_section_content("Steps", "")
        if steps:
            step_lines = [
                line for line in steps.split("\n")
                if line.strip() and line.strip()[0].isdigit()
            ]
            if len(step_lines) > 0 and len(steps.split()) / len(step_lines) < 10:
                issues.append(
                    ValidationIssue(
                        file=self.path,
                        issue="Plan steps may be too vague to execute",
                        severity=IssueSeverity.INFO,
                        validator="validate_content",
                        section="Steps",
                        suggestion="Add detail so steps are unambiguous",
                        requires_llm=True,
                    )
                )

        # Check verification completeness
        verification = self.get_section_content("Verification", "")
        if verification:
            items = [
                line for line in verification.split("\n")
                if line.strip().startswith("-")
            ]
            if len(items) < 2:
                issues.append(
                    ValidationIssue(
                        file=self.path,
                        issue="Verification section may not have enough criteria",
                        severity=IssueSeverity.INFO,
                        validator="validate_content",
                        section="Verification",
                        suggestion="Add verification criteria for each objective",
                        requires_llm=True,
                    )
                )

        return issues
