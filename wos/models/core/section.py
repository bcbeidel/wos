"""DocumentSection value object."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from wos.models.core.enums import IssueSeverity
from wos.models.core.validation_issue import ValidationIssue


class DocumentSection(BaseModel):
    """A single H2 section within a document.

    Value object — immutable and hashable via frozen=True.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    content: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    # ── String representations ────────────────────────────────────

    def __str__(self) -> str:
        return f"## {self.name} ({self.word_count} words)"

    def __repr__(self) -> str:
        lines = f", lines {self.line_start}-{self.line_end}" if self.line_start else ""
        return f"DocumentSection(name={self.name!r}, words={self.word_count}{lines})"

    # ── Properties ────────────────────────────────────────────────

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + 1 if self.content else 0

    # ── JSON protocol ─────────────────────────────────────────────

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> DocumentSection:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls.model_validate(data)

    # ── Markdown protocol ─────────────────────────────────────────

    def to_markdown(self) -> str:
        """Return markdown heading and content: ## Name\\n\\nContent."""
        return f"## {self.name}\n\n{self.content}"

    # ── Token estimation ──────────────────────────────────────────

    def get_estimated_tokens(self) -> int:
        """Estimate token cost of this section."""
        return len(self.name) // 4 + 2 + len(self.content) // 4

    # ── Validation protocol ───────────────────────────────────────

    def validate_self(self, deep: bool = False) -> List[ValidationIssue]:
        """Check internal consistency.

        Returns list[ValidationIssue] — empty when this section is well-formed.
        """
        issues: List[ValidationIssue] = []
        if not self.name.strip():
            issues.append(
                ValidationIssue(
                    file="<DocumentSection>",
                    issue="Section name is blank or whitespace-only",
                    severity=IssueSeverity.WARN,
                    validator="DocumentSection.validate_self",
                    suggestion="Provide a descriptive section name",
                )
            )
        return issues

    @property
    def is_valid(self) -> bool:
        """Shortcut: True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0
