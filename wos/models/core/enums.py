"""Enums and type groupings for WOS document system."""

from __future__ import annotations

from enum import Enum


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
