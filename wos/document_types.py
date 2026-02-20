"""Document type models, dispatch tables, and parse/validate functions.

This module is a backward-compatibility re-export layer. All types are
now defined in the ``wos.models`` package. Existing callers that do
``from wos.document_types import X`` continue to work unchanged.
"""

from __future__ import annotations

# Re-export everything from the models package
from wos.models import (  # noqa: F401
    ARTIFACT_TYPES,
    CONTEXT_TYPES,
    DATE_PREFIX_TYPES,
    DIRECTORY_PATTERNS,
    FRESHNESS_TRACKED_TYPES,
    OPTIONAL_SECTIONS,
    SECTIONS,
    SIZE_BOUNDS,
    SOURCE_GROUNDED_TYPES,
    BaseDocument,
    CitedSource,
    ContextArea,
    Document,
    DocumentSection,
    DocumentType,
    Frontmatter,
    FrontmatterBase,
    HealthReport,
    IssueSeverity,
    NoteDocument,
    NoteFrontmatter,
    OverviewDocument,
    OverviewFrontmatter,
    PlanDocument,
    PlanFrontmatter,
    PlanStatus,
    ResearchDocument,
    ResearchFrontmatter,
    SectionSpec,
    SizeBounds,
    Source,
    TopicDocument,
    TopicFrontmatter,
    ValidationIssue,
    parse_document,
)
