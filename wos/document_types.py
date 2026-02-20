"""Document type models, dispatch tables, and parse/validate functions.

This is the shared foundation for all skills and scripts. Everything
derives from these models — templates, validators, discovery, and CLI
tools all import from here.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated, Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

# ── Enums ────────────────────────────────────────────────────────


class DocumentType(str, Enum):
    OVERVIEW = "overview"
    TOPIC = "topic"
    RESEARCH = "research"
    PLAN = "plan"
    NOTE = "note"


class IssueSeverity(str, Enum):
    FAIL = "fail"
    WARN = "warn"
    INFO = "info"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETE = "complete"
    ABANDONED = "abandoned"


# ── Validation issue model ────────────────────────────────────────


class ValidationIssue(BaseModel):
    """A single validation issue found during document health checks."""

    file: str
    issue: str
    severity: IssueSeverity
    validator: str
    section: Optional[str] = None
    suggestion: Optional[str] = None


# ── Type groupings for validation dispatch ───────────────────────

CONTEXT_TYPES = {DocumentType.OVERVIEW, DocumentType.TOPIC}
ARTIFACT_TYPES = {DocumentType.RESEARCH, DocumentType.PLAN}
SOURCE_GROUNDED_TYPES = {DocumentType.TOPIC, DocumentType.RESEARCH}
FRESHNESS_TRACKED_TYPES = {DocumentType.TOPIC, DocumentType.OVERVIEW}


# ── Shared models ────────────────────────────────────────────────


class Source(BaseModel):
    """A cited source with URL and title."""

    url: str
    title: str


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
    status: Optional[PlanStatus] = None


class PlanFrontmatter(FrontmatterBase):
    document_type: Literal["plan"]
    status: PlanStatus


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
    """Defines a required section for a document type."""

    name: str
    position: int  # 1-indexed canonical position
    min_words: Optional[int] = None


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


# ── Markdown splitting ───────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _split_markdown(
    content: str,
) -> tuple[dict, str, dict[str, str], str]:
    """Parse YAML frontmatter, title, and sections from markdown.

    Returns (frontmatter_dict, title, sections, raw_content).

    Raises ValidationError if no YAML frontmatter is found.
    Sections are keyed by H2 heading name; H3+ headings are content
    within their parent H2 section.
    """
    fm_match = _FRONTMATTER_RE.match(content)
    if not fm_match:
        raise ValidationError.from_exception_data(
            title="Document",
            line_errors=[
                {
                    "type": "value_error",
                    "loc": ("frontmatter",),
                    "msg": "No YAML frontmatter found (expected --- delimiters)",
                    "input": content[:100],
                    "ctx": {"error": ValueError("No YAML frontmatter found")},
                }
            ],
        )

    frontmatter_yaml = fm_match.group(1)
    frontmatter_dict = yaml.safe_load(frontmatter_yaml) or {}

    body = content[fm_match.end() :]

    # Extract title from first H1
    h1_match = _H1_RE.search(body)
    title = h1_match.group(1).strip() if h1_match else ""

    # Extract sections by H2 headings
    sections: dict[str, str] = {}
    h2_matches = list(_H2_RE.finditer(body))
    for i, m in enumerate(h2_matches):
        section_name = m.group(1).strip()
        start = m.end()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(body)
        sections[section_name] = body[start:end].strip()

    return frontmatter_dict, title, sections, content


# ── Document model ───────────────────────────────────────────────


class Document(BaseModel):
    """A complete parsed knowledge record."""

    path: str
    frontmatter: Frontmatter  # discriminated union dispatches here
    title: str
    sections: Dict[str, str]  # section_name -> section_content
    raw_content: str

    @property
    def document_type(self) -> DocumentType:
        return DocumentType(self.frontmatter.document_type)

    @property
    def required_sections(self) -> list[SectionSpec]:
        return SECTIONS[self.document_type]

    @property
    def size_bounds(self) -> SizeBounds:
        return SIZE_BOUNDS[self.document_type]


# ── Public API ───────────────────────────────────────────────────


def parse_document(path: str, content: str) -> Document:
    """Parse a markdown file into a validated Document.

    Raises ValidationError with clear messages on:
    - Missing or invalid YAML frontmatter
    - Missing or invalid frontmatter fields
    - Wrong document_type value
    - Invalid dates, empty sources, bad status values
    - Type-specific field violations
    """
    frontmatter_dict, title, sections, raw = _split_markdown(content)

    # Validate frontmatter via discriminated union — this gives clear
    # error messages for missing fields, wrong types, etc.
    from pydantic import TypeAdapter

    adapter = TypeAdapter(Frontmatter)
    frontmatter = adapter.validate_python(frontmatter_dict)

    return Document(
        path=path,
        frontmatter=frontmatter,
        title=title,
        sections=sections,
        raw_content=raw,
    )
