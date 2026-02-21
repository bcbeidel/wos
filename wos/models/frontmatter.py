"""Frontmatter models and structural dispatch tables.

Each document type has a Pydantic frontmatter model with type-specific
fields and validators. The discriminated union dispatches based on the
``document_type`` field.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wos.models.core import (
    CitedSource,
    DocumentType,
    Source,
)


# ── Shared base ─────────────────────────────────────────────────


class FrontmatterBase(BaseModel):
    """Fields common to all four document types."""

    description: str = Field(min_length=10)
    last_updated: date

    # Optional fields available on all types
    tags: Optional[List[str]] = None
    related: Optional[List[str]] = None

    @field_validator("last_updated")
    @classmethod
    def not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("last_updated must not be in the future")
        return v

    @field_validator("tags")
    @classmethod
    def tags_lowercase_hyphenated(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for tag in v:
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", tag):
                raise ValueError(
                    f"tag '{tag}' must be lowercase hyphenated "
                    f"(e.g., 'api-design', 'caching')"
                )
        return v


# ── Type-specific frontmatter models ─────────────────────────────


class TopicFrontmatter(FrontmatterBase):
    document_type: Literal["topic"]
    sources: List[Source] = Field(min_length=1)
    last_validated: date

    @field_validator("last_validated")
    @classmethod
    def validated_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("last_validated must not be in the future")
        return v


class OverviewFrontmatter(FrontmatterBase):
    document_type: Literal["overview"]
    last_validated: date

    @field_validator("last_validated")
    @classmethod
    def validated_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("last_validated must not be in the future")
        return v


class ResearchFrontmatter(FrontmatterBase):
    document_type: Literal["research"]
    sources: List[Source] = Field(min_length=1)


class PlanFrontmatter(FrontmatterBase):
    document_type: Literal["plan"]
    status: Optional[str] = None


class NoteFrontmatter(BaseModel):
    """Minimal frontmatter for generic notes — no structural requirements."""

    document_type: Literal["note"]
    description: str = Field(min_length=10)

    # Optional fields — same validation as other types
    tags: Optional[List[str]] = None
    related: Optional[List[str]] = None

    @field_validator("tags")
    @classmethod
    def tags_lowercase_hyphenated(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        if v is None:
            return v
        for tag in v:
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", tag):
                raise ValueError(
                    f"tag '{tag}' must be lowercase hyphenated "
                    f"(e.g., 'api-design', 'caching')"
                )
        return v


# ── Discriminated union ──────────────────────────────────────────

Frontmatter = Annotated[
    Union[
        TopicFrontmatter,
        OverviewFrontmatter,
        ResearchFrontmatter,
        PlanFrontmatter,
        NoteFrontmatter,
    ],
    Field(discriminator="document_type"),
]


# ── Structural dispatch tables ───────────────────────────────────


class SectionSpec(BaseModel):
    """Defines a required section for a document type.

    Value object — immutable and hashable via frozen=True.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    position: int  # 1-indexed canonical position
    min_words: Optional[int] = None

    # ── String representations ────────────────────────────────────

    def __str__(self) -> str:
        return f"{self.name} @{self.position}"

    def __repr__(self) -> str:
        return f"SectionSpec(name={self.name!r}, position={self.position})"

    # ── JSON protocol ─────────────────────────────────────────────

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> SectionSpec:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls.model_validate(data)

    # ── Validation protocol ───────────────────────────────────────

    def validate_self(self) -> List:
        """Check internal consistency.

        Returns list[ValidationIssue] — empty when this spec is well-formed.
        """
        from wos.models.core import ValidationIssue, IssueSeverity

        issues = []
        if not self.name.strip():
            issues.append(
                ValidationIssue(
                    file="<SectionSpec>",
                    issue="Section name is blank",
                    severity=IssueSeverity.WARN,
                    validator="SectionSpec.validate_self",
                    suggestion="Provide a section name",
                )
            )
        if self.position < 1:
            issues.append(
                ValidationIssue(
                    file="<SectionSpec>",
                    issue=f"Position {self.position} is less than 1",
                    severity=IssueSeverity.WARN,
                    validator="SectionSpec.validate_self",
                    suggestion="Position must be 1 or greater",
                )
            )
        return issues

    @property
    def is_valid(self) -> bool:
        """Shortcut: True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0


SECTIONS: Dict[DocumentType, List[SectionSpec]] = {
    DocumentType.TOPIC: [
        SectionSpec(name="Guidance", position=1),
        SectionSpec(name="Context", position=2),
        SectionSpec(name="In Practice", position=3),
        SectionSpec(name="Pitfalls", position=4),
        SectionSpec(name="Go Deeper", position=5),
    ],
    DocumentType.OVERVIEW: [
        SectionSpec(name="What This Covers", position=1, min_words=30),
        SectionSpec(name="Topics", position=2),
        SectionSpec(name="Key Sources", position=3),
    ],
    DocumentType.RESEARCH: [
        SectionSpec(name="Question", position=1),
        SectionSpec(name="Findings", position=2),
        SectionSpec(name="Implications", position=3),
        SectionSpec(name="Sources", position=4),
    ],
    DocumentType.PLAN: [
        SectionSpec(name="Objective", position=1),
        SectionSpec(name="Context", position=2),
        SectionSpec(name="Steps", position=3),
        SectionSpec(name="Verification", position=4),
    ],
    DocumentType.NOTE: [],
}

OPTIONAL_SECTIONS: Dict[DocumentType, Dict[str, Dict[str, str]]] = {
    DocumentType.TOPIC: {
        "Quick Reference": {"after": "Pitfalls", "before": "Go Deeper"},
    },
    DocumentType.NOTE: {},
}


class SizeBounds(BaseModel):
    """Min/max line counts for a document type."""

    min_lines: int
    max_lines: Optional[int] = None  # None = no upper bound


SIZE_BOUNDS: Dict[DocumentType, SizeBounds] = {
    DocumentType.TOPIC: SizeBounds(min_lines=10, max_lines=500),
    DocumentType.OVERVIEW: SizeBounds(min_lines=5, max_lines=150),
    DocumentType.RESEARCH: SizeBounds(min_lines=20),
    DocumentType.PLAN: SizeBounds(min_lines=10),
    DocumentType.NOTE: SizeBounds(min_lines=1),
}

DIRECTORY_PATTERNS: Dict[DocumentType, str] = {
    DocumentType.TOPIC: r"context/[\w-]+/[a-z0-9][\w-]*\.md$",
    DocumentType.OVERVIEW: r"context/[\w-]+/_overview\.md$",
    DocumentType.RESEARCH: r"artifacts/research/.*\d{4}-\d{2}-\d{2}-[\w-]+\.md$",
    DocumentType.PLAN: r"artifacts/plans/.*\d{4}-\d{2}-\d{2}-[\w-]+\.md$",
}

DATE_PREFIX_TYPES = {DocumentType.RESEARCH, DocumentType.PLAN}
