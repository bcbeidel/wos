"""Core types: enums, ValidationIssue, DocumentSection, CitedSource.

These are leaf types with no dependencies on other wos.models modules.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


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


# ── Type groupings for validation dispatch ───────────────────────

CONTEXT_TYPES = {DocumentType.OVERVIEW, DocumentType.TOPIC}
ARTIFACT_TYPES = {DocumentType.RESEARCH, DocumentType.PLAN}
SOURCE_GROUNDED_TYPES = {DocumentType.TOPIC, DocumentType.RESEARCH}
FRESHNESS_TRACKED_TYPES = {DocumentType.TOPIC, DocumentType.OVERVIEW}


# ── Validation issue model ────────────────────────────────────────


class ValidationIssue(BaseModel):
    """A single validation issue found during document health checks."""

    file: str
    issue: str
    severity: IssueSeverity
    validator: str
    section: Optional[str] = None
    suggestion: Optional[str] = None


# ── Section model ────────────────────────────────────────────────


class DocumentSection(BaseModel):
    """A single H2 section within a document."""

    name: str
    content: str

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + 1 if self.content else 0


# ── Cited source model ──────────────────────────────────────────


class CitedSource(BaseModel):
    """A cited source with URL and title."""

    url: str
    title: str

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
