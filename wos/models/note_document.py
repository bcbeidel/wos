"""NoteDocument — generic note with minimal structure."""

from __future__ import annotations

from wos.models.base_document import BaseDocument
from wos.models.validation_issue import ValidationIssue


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

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        from wos.validators import check_title_heading

        issues: list[ValidationIssue] = []
        issues.extend(check_title_heading(self))
        return issues

    def validate_content(self) -> list:
        return []
