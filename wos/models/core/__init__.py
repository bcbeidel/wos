"""Core types re-export layer.

Preserves backward compatibility for ``from wos.models.core import X``.
Actual implementations live in focused modules:
  - enums.py: DocumentType, IssueSeverity, type groupings
  - validation_issue.py: ValidationIssue
  - section.py: DocumentSection
  - cited_source.py: CitedSource (+ Source alias)
  - protocol.py: WosDomainObject
"""

from __future__ import annotations

from wos.models.core.cited_source import CitedSource, Source  # noqa: F401

# ── Re-exports ────────────────────────────────────────────────────
from wos.models.core.enums import (  # noqa: F401
    ARTIFACT_TYPES,
    CONTEXT_TYPES,
    FRESHNESS_TRACKED_TYPES,
    SOURCE_GROUNDED_TYPES,
    DocumentType,
    IssueSeverity,
)
from wos.models.core.protocol import WosDomainObject  # noqa: F401
from wos.models.core.section import DocumentSection  # noqa: F401
from wos.models.core.validation_issue import ValidationIssue  # noqa: F401
