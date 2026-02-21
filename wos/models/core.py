"""Core types: enums, ValidationIssue, DocumentSection, CitedSource.

These are leaf types with no dependencies on other wos.models modules.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


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
    PASS = "pass"


# ── Type groupings for validation dispatch ───────────────────────

CONTEXT_TYPES = {DocumentType.OVERVIEW, DocumentType.TOPIC}
ARTIFACT_TYPES = {DocumentType.RESEARCH, DocumentType.PLAN}
SOURCE_GROUNDED_TYPES = {DocumentType.TOPIC, DocumentType.RESEARCH}
FRESHNESS_TRACKED_TYPES = {DocumentType.TOPIC, DocumentType.OVERVIEW}


# ── Validation issue model ────────────────────────────────────────


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
        parts = [f"- **{self.severity.value.upper()}** `{self.file}`: {self.issue}"]
        if self.suggestion:
            parts.append(f"  - {self.suggestion}")
        return "\n".join(parts)

    # ── Validation protocol ───────────────────────────────────────

    def validate_self(self) -> List[ValidationIssue]:
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


# ── Section model ────────────────────────────────────────────────


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

    def validate_self(self) -> List[ValidationIssue]:
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


# ── Cited source model ──────────────────────────────────────────


class CitedSource(BaseModel):
    """A cited source with URL and title.

    Value object — immutable and hashable via frozen=True.
    """

    model_config = ConfigDict(frozen=True)

    url: str
    title: str

    # ── String representations ────────────────────────────────────

    def __str__(self) -> str:
        return f"[{self.title}]({self.url})"

    def __repr__(self) -> str:
        return f"CitedSource(url={self.url!r}, title={self.title!r})"

    # ── JSON protocol ─────────────────────────────────────────────

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, data: dict) -> CitedSource:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls.model_validate(data)

    # ── Markdown protocol ─────────────────────────────────────────

    def to_markdown(self) -> str:
        """Return markdown link: [title](url)."""
        return f"[{self.title}]({self.url})"

    @classmethod
    def from_markdown_link(cls, md_link: str) -> CitedSource:
        """Parse a markdown link ``[title](url)`` into a CitedSource.

        Raises ValueError if the string is not a valid markdown link.
        """
        match = re.match(r"^\[(.+?)]\((.+?)\)$", md_link.strip())
        if not match:
            raise ValueError(f"Invalid markdown link: {md_link!r}")
        return cls(title=match.group(1), url=match.group(2))

    # ── YAML protocol ─────────────────────────────────────────────

    def to_yaml_entry(self) -> str:
        """Return a YAML source entry (two lines: url and title).

        Values are YAML-escaped (backslashes and double-quotes).
        """
        esc_url = self.url.replace("\\", "\\\\").replace('"', '\\"')
        esc_title = self.title.replace("\\", "\\\\").replace('"', '\\"')
        return f'url: "{esc_url}"\ntitle: "{esc_title}"'

    # ── Validation protocol ───────────────────────────────────────

    def validate_self(self, deep: bool = False) -> List[ValidationIssue]:
        """Check internal consistency.

        Shallow (default): checks url scheme (http/https) and title not blank.
        Deep: also runs check_reachability() and converts to ValidationIssue.

        Returns list[ValidationIssue].
        """
        from urllib.parse import urlparse as _urlparse

        issues: List[ValidationIssue] = []

        # Check URL scheme
        parsed = _urlparse(self.url)
        if parsed.scheme not in ("http", "https"):
            issues.append(
                ValidationIssue(
                    file="<CitedSource>",
                    issue=f"URL scheme '{parsed.scheme}' is not http/https: {self.url}",
                    severity=IssueSeverity.WARN,
                    validator="CitedSource.validate_self",
                    suggestion="Use an http:// or https:// URL",
                )
            )

        # Check title not blank
        if not self.title.strip():
            issues.append(
                ValidationIssue(
                    file="<CitedSource>",
                    issue="Title is blank or whitespace-only",
                    severity=IssueSeverity.WARN,
                    validator="CitedSource.validate_self",
                    suggestion="Provide a descriptive title for the source",
                )
            )

        # Deep validation: network reachability
        if deep:
            result = self.check_reachability()
            if not result.reachable:
                issues.append(
                    ValidationIssue(
                        file="<CitedSource>",
                        issue=f"URL not reachable: {result.reason}",
                        severity=IssueSeverity.WARN,
                        validator="CitedSource.validate_self",
                        section=None,
                        suggestion="Verify the URL is correct and accessible",
                    )
                )

        return issues

    @property
    def is_valid(self) -> bool:
        """Shortcut: True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0

    # ── Existing methods (unchanged) ──────────────────────────────

    def normalize_title(self) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = self.title.lower()
        text = text.replace("\u2013", " ").replace("\u2014", " ")
        text = re.sub(r"[^a-z0-9 ]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_estimated_tokens(self) -> int:
        """Estimate token cost of this source citation."""
        return len(self.url) // 3 + len(self.title) // 4 + 5

    def check_reachability(self):
        """HTTP HEAD check. Returns ReachabilityResult."""
        from wos.source_verification import check_url_reachability

        return check_url_reachability(self.url)

    def verify(self):
        """Full verification — reachability + title match. Returns VerificationResult."""
        from wos.source_verification import verify_source

        return verify_source(self.url, self.title)


# Backward compat alias
Source = CitedSource
