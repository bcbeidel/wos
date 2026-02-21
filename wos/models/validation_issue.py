"""ValidationIssue value object."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from wos.models.enums import IssueSeverity


class ValidationIssue(BaseModel):
    """A single validation issue found during document health checks.

    Value object — immutable and hashable via frozen=True.
    """

    model_config = ConfigDict(frozen=True)

    file: str
    issue: str
    severity: IssueSeverity
    validator: str
    section: Optional[str] = None
    suggestion: Optional[str] = None
    requires_llm: bool = False

    # ── String representations ────────────────────────────────────

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.file}: {self.issue}"

    def __repr__(self) -> str:
        return (
            f"ValidationIssue(file={self.file!r}, issue={self.issue!r}, "
            f"severity={self.severity.value!r}, validator={self.validator!r})"
        )

    # ── JSON protocol ─────────────────────────────────────────────

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> ValidationIssue:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls.model_validate(data)

    # ── Markdown protocol ─────────────────────────────────────────

    def to_markdown(self) -> str:
        """Return markdown list item: - **SEVERITY** `file`: issue."""
        label = "LLM-REVIEW" if self.requires_llm else self.severity.value.upper()
        parts = [f"- **{label}** `{self.file}`: {self.issue}"]
        if self.suggestion:
            parts.append(f"  - {self.suggestion}")
        return "\n".join(parts)

    # ── Validation protocol ───────────────────────────────────────

    def validate_self(self, deep: bool = False) -> List[ValidationIssue]:
        """Check internal consistency.

        Returns list[ValidationIssue] — empty when this issue is well-formed.
        """
        issues: List[ValidationIssue] = []
        if not self.issue.strip():
            issues.append(
                ValidationIssue(
                    file="<ValidationIssue>",
                    issue="Issue text is blank or whitespace-only",
                    severity=IssueSeverity.WARN,
                    validator="ValidationIssue.validate_self",
                    suggestion="Provide a descriptive issue message",
                )
            )
        return issues

    @property
    def is_valid(self) -> bool:
        """Shortcut: True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0
