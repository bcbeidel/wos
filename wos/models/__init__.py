"""WOS domain models package.

Re-exports all public symbols so callers can use either:
    from wos.models import Document, parse_document
    from wos.models.core import DocumentType  # direct sub-module access
"""

from __future__ import annotations

# ── Enums & type groupings ─────────────────────────────────────
from wos.models.enums import (
    ARTIFACT_TYPES,
    CONTEXT_TYPES,
    FRESHNESS_TRACKED_TYPES,
    SOURCE_GROUNDED_TYPES,
    DocumentType,
    IssueSeverity,
)

# ── Core value objects ─────────────────────────────────────────
from wos.models.validation_issue import ValidationIssue
from wos.models.section import DocumentSection
from wos.models.cited_source import CitedSource, Source

# ── Frontmatter models & dispatch tables ────────────────────────
from wos.models.frontmatter import (
    DATE_PREFIX_TYPES,
    DIRECTORY_PATTERNS,
    OPTIONAL_SECTIONS,
    SECTIONS,
    SIZE_BOUNDS,
    Frontmatter,
    FrontmatterBase,
    NoteFrontmatter,
    OverviewFrontmatter,
    PlanFrontmatter,
    ResearchFrontmatter,
    SectionSpec,
    SizeBounds,
    TopicFrontmatter,
)

# ── Document models ─────────────────────────────────────────────
from wos.models.documents import (
    BaseDocument,
    Document,
    NoteDocument,
    OverviewDocument,
    PlanDocument,
    ResearchDocument,
    TopicDocument,
)

# ── Context area ───────────────────────────────────────────────
from wos.models.context_area import ContextArea

# ── Health report ──────────────────────────────────────────────
from wos.models.health_report import HealthReport

# ── Protocol ──────────────────────────────────────────────────
from wos.models.protocol import WosDomainObject

# ── Parsing ─────────────────────────────────────────────────────
from wos.models.parsing import parse_document

__all__ = [
    # Enums
    "DocumentType",
    "IssueSeverity",
    # Type groupings
    "ARTIFACT_TYPES",
    "CONTEXT_TYPES",
    "FRESHNESS_TRACKED_TYPES",
    "SOURCE_GROUNDED_TYPES",
    # Validation
    "ValidationIssue",
    # Section
    "DocumentSection",
    # Source
    "CitedSource",
    "Source",
    # Frontmatter
    "Frontmatter",
    "FrontmatterBase",
    "TopicFrontmatter",
    "OverviewFrontmatter",
    "ResearchFrontmatter",
    "PlanFrontmatter",
    "NoteFrontmatter",
    # Dispatch tables
    "SECTIONS",
    "OPTIONAL_SECTIONS",
    "SectionSpec",
    "SizeBounds",
    "SIZE_BOUNDS",
    "DIRECTORY_PATTERNS",
    "DATE_PREFIX_TYPES",
    # Documents
    "BaseDocument",
    "Document",
    "TopicDocument",
    "OverviewDocument",
    "ResearchDocument",
    "PlanDocument",
    "NoteDocument",
    # Context area
    "ContextArea",
    # Health report
    "HealthReport",
    # Protocol
    "WosDomainObject",
    # Parsing
    "parse_document",
]
