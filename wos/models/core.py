"""Core types re-export layer.

Preserves backward compatibility for ``from wos.models.core import X``.
Actual implementations live in focused modules:
  - enums.py: DocumentType, IssueSeverity, type groupings
  - validation_issue.py: ValidationIssue
  - section.py: DocumentSection
  - cited_source.py: CitedSource (+ Source alias)
"""

from __future__ import annotations

# ── Re-exports ────────────────────────────────────────────────────

from wos.models.enums import (  # noqa: F401
    ARTIFACT_TYPES,
    CONTEXT_TYPES,
    FRESHNESS_TRACKED_TYPES,
    SOURCE_GROUNDED_TYPES,
    DocumentType,
    IssueSeverity,
)
from wos.models.validation_issue import ValidationIssue  # noqa: F401
from wos.models.section import DocumentSection  # noqa: F401
from wos.models.cited_source import CitedSource, Source  # noqa: F401
