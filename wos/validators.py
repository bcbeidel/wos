"""Per-file validators — standalone functions called by document subclasses.

Each validator function takes a Document and returns list[ValidationIssue].
Dispatch is handled by each document subclass's validate_self() method.
"""

from __future__ import annotations

import re
from datetime import date
from typing import List
from urllib.parse import urlparse

from wos.document_types import (
    DIRECTORY_PATTERNS,
    FRESHNESS_TRACKED_TYPES,
    SECTIONS,
    Document,
    DocumentType,
    IssueSeverity,
    ValidationIssue,
)

# ── Shared validators (all types) ───────────────────────────────


def _format_section_list(doc_type: DocumentType) -> str:
    """Format the canonical section list for a document type."""
    names = [f"## {s.name}" for s in SECTIONS[doc_type]]
    prefix = f"{doc_type.value.capitalize()} documents require"
    return f"{prefix} these sections in order: {', '.join(names)}"


def check_section_presence(doc: Document) -> List[ValidationIssue]:
    """Check that all required sections exist."""
    issues: List[ValidationIssue] = []
    required = doc.required_sections
    section_hint = _format_section_list(doc.document_type)
    for spec in required:
        if not doc.has_section(spec.name):
            issues.append(
                ValidationIssue(
                    file=doc.path,
                    issue=f"Missing required section: ## {spec.name}",
                    severity=IssueSeverity.WARN,
                    validator="check_section_presence",
                    section=spec.name,
                    suggestion=f"Add a ## {spec.name} section. {section_hint}",
                )
            )
    return issues


def check_section_ordering(doc: Document) -> List[ValidationIssue]:
    """Check that sections appear in canonical order."""
    issues: List[ValidationIssue] = []
    required = doc.required_sections
    section_names = doc.section_names

    # Build ordered list of required sections that are present
    present = [s for s in required if s.name in section_names]
    if len(present) < 2:
        return issues

    for i in range(len(present) - 1):
        idx_a = section_names.index(present[i].name)
        idx_b = section_names.index(present[i + 1].name)
        if idx_a > idx_b:
            section_hint = _format_section_list(doc.document_type)
            issues.append(
                ValidationIssue(
                    file=doc.path,
                    issue=f"Section ## {present[i + 1].name} appears before "
                    f"## {present[i].name} (expected after)",
                    severity=IssueSeverity.WARN,
                    validator="check_section_ordering",
                    suggestion="Reorder sections to match "
                    f"canonical order. {section_hint}",
                )
            )
            break  # Report first misordering only

    return issues


def check_size_bounds(doc: Document) -> List[ValidationIssue]:
    """Check document size against bounds."""
    issues: List[ValidationIssue] = []
    bounds = doc.size_bounds
    lines = doc.raw_content.count("\n") + 1

    if lines < bounds.min_lines:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"Document is {lines} lines, minimum is {bounds.min_lines}",
                severity=IssueSeverity.WARN,
                validator="check_size_bounds",
                suggestion="Add more content to meet minimum size",
            )
        )

    if bounds.max_lines and lines > bounds.max_lines:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"Document is {lines} lines, maximum is {bounds.max_lines}",
                severity=IssueSeverity.WARN,
                validator="check_size_bounds",
                suggestion="Consider splitting into smaller documents",
            )
        )

    return issues


def check_directory_placement(doc: Document) -> List[ValidationIssue]:
    """Check that the file path matches expected directory pattern."""
    issues: List[ValidationIssue] = []
    pattern = DIRECTORY_PATTERNS.get(doc.document_type)
    if pattern and not re.search(pattern, doc.path):
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"File path does not match expected pattern for "
                f"{doc.document_type.value}: {pattern}",
                severity=IssueSeverity.WARN,
                validator="check_directory_placement",
                suggestion="Move file to the correct directory",
            )
        )
    return issues


def check_title_heading(doc: Document) -> List[ValidationIssue]:
    """Check that an H1 title exists."""
    issues: List[ValidationIssue] = []
    if not doc.title:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue="No H1 title heading found",
                severity=IssueSeverity.WARN,
                validator="check_title_heading",
                suggestion="Add a # Title heading after the frontmatter",
            )
        )
    return issues


def check_heading_hierarchy(doc: Document) -> List[ValidationIssue]:
    """Check that heading levels don't skip (e.g., H1 -> H3)."""
    issues: List[ValidationIssue] = []
    heading_re = re.compile(r"^(#{1,6})\s+", re.MULTILINE)
    levels = [len(m.group(1)) for m in heading_re.finditer(doc.raw_content)]

    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            issues.append(
                ValidationIssue(
                    file=doc.path,
                    issue=f"Heading level skips from H{levels[i - 1]} to "
                    f"H{levels[i]}",
                    severity=IssueSeverity.INFO,
                    validator="check_heading_hierarchy",
                    suggestion="Use sequential heading levels",
                )
            )
            break

    return issues


def check_placeholder_comments(doc: Document) -> List[ValidationIssue]:
    """Check for TODO/FIXME HTML comments that indicate incomplete content."""
    issues: List[ValidationIssue] = []
    placeholder_re = re.compile(
        r"<!--\s*(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE
    )
    matches = placeholder_re.findall(doc.raw_content)
    if matches:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"Found {len(matches)} placeholder comment(s): "
                f"{', '.join(set(m.upper() for m in matches))}",
                severity=IssueSeverity.INFO,
                validator="check_placeholder_comments",
                suggestion="Replace placeholder comments with real content",
            )
        )
    return issues


def check_date_fields(doc: Document) -> List[ValidationIssue]:
    """Check date field consistency."""
    issues: List[ValidationIssue] = []
    fm = doc.frontmatter

    # Check last_validated vs last_updated (if both exist)
    if hasattr(fm, "last_validated") and fm.last_validated:
        if fm.last_validated > fm.last_updated:
            issues.append(
                ValidationIssue(
                    file=doc.path,
                    issue="last_validated is after last_updated",
                    severity=IssueSeverity.WARN,
                    validator="check_date_fields",
                    suggestion="Update last_updated to match or follow "
                    "last_validated",
                )
            )

    return issues


# ── Type-specific validators ─────────────────────────────────────

# Staleness thresholds
_STALE_INFO_DAYS = 30
_STALE_WARN_DAYS = 60
_STALE_FAIL_DAYS = 90


def check_last_validated(doc: Document) -> List[ValidationIssue]:
    """Check staleness of last_validated date.

    Only applicable to FRESHNESS_TRACKED_TYPES (topic, overview).
    Research and plan documents are NOT checked.
    """
    issues: List[ValidationIssue] = []
    if doc.document_type not in FRESHNESS_TRACKED_TYPES:
        return issues

    fm = doc.frontmatter
    if not hasattr(fm, "last_validated") or not fm.last_validated:
        return issues

    age = (date.today() - fm.last_validated).days

    if age >= _STALE_FAIL_DAYS:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"Last validated {age} days ago (threshold: {_STALE_FAIL_DAYS}d)",
                severity=IssueSeverity.WARN,
                validator="check_last_validated",
                suggestion="Review and revalidate this document",
            )
        )
    elif age >= _STALE_WARN_DAYS:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"Last validated {age} days ago (threshold: {_STALE_WARN_DAYS}d)",
                severity=IssueSeverity.WARN,
                validator="check_last_validated",
                suggestion="Consider reviewing this document for currency",
            )
        )
    elif age >= _STALE_INFO_DAYS:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"Last validated {age} days ago (threshold: {_STALE_INFO_DAYS}d)",
                severity=IssueSeverity.INFO,
                validator="check_last_validated",
                suggestion="Document is getting stale",
            )
        )

    return issues


def check_source_diversity(doc: Document) -> List[ValidationIssue]:
    """Check that sources come from multiple domains."""
    issues: List[ValidationIssue] = []
    fm = doc.frontmatter
    if not hasattr(fm, "sources") or not fm.sources:
        return issues

    domains = set()
    for source in fm.sources:
        parsed = urlparse(source.url)
        if parsed.hostname:
            domains.add(parsed.hostname)

    if len(fm.sources) > 1 and len(domains) < 2:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"All {len(fm.sources)} sources come from the same domain",
                severity=IssueSeverity.INFO,
                validator="check_source_diversity",
                suggestion="Add sources from different domains for diversity",
            )
        )

    return issues


def check_go_deeper_links(doc: Document) -> List[ValidationIssue]:
    """Check that the Go Deeper section contains links (topic only)."""
    issues: List[ValidationIssue] = []
    if doc.document_type != DocumentType.TOPIC:
        return issues

    go_deeper = doc.get_section_content("Go Deeper")
    if go_deeper and not re.search(r"\[.+\]\(.+\)", go_deeper):
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue="Go Deeper section has no links",
                severity=IssueSeverity.INFO,
                validator="check_go_deeper_links",
                section="Go Deeper",
                suggestion="Add links to further reading",
            )
        )

    return issues


def check_what_this_covers_length(doc: Document) -> List[ValidationIssue]:
    """Check that the What This Covers section meets minimum word count."""
    issues: List[ValidationIssue] = []
    if doc.document_type != DocumentType.OVERVIEW:
        return issues

    section = doc.get_section_content("What This Covers")
    word_count = len(section.split())
    min_words = 30  # From SectionSpec

    if section and word_count < min_words:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"What This Covers has {word_count} words "
                f"(minimum: {min_words})",
                severity=IssueSeverity.WARN,
                validator="check_what_this_covers_length",
                section="What This Covers",
                suggestion="Expand the section description",
            )
        )

    return issues


def check_question_nonempty(doc: Document) -> List[ValidationIssue]:
    """Check that research Question section is not empty."""
    issues: List[ValidationIssue] = []
    if doc.document_type != DocumentType.RESEARCH:
        return issues

    question = doc.get_section_content("Question")
    if not question.strip():
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue="Question section is empty",
                severity=IssueSeverity.FAIL,
                validator="check_question_nonempty",
                section="Question",
                suggestion="State the research question clearly",
            )
        )

    return issues


def check_date_prefix_matches(doc: Document) -> List[ValidationIssue]:
    """Check that filename date prefix matches frontmatter last_updated."""
    issues: List[ValidationIssue] = []
    if doc.document_type not in {DocumentType.RESEARCH, DocumentType.PLAN}:
        return issues

    # Extract date from filename
    match = re.search(r"(\d{4}-\d{2}-\d{2})", doc.path)
    if not match:
        return issues

    filename_date = match.group(1)
    fm_date = doc.frontmatter.last_updated.isoformat()

    if filename_date != fm_date:
        issues.append(
            ValidationIssue(
                file=doc.path,
                issue=f"Filename date ({filename_date}) differs from "
                f"last_updated ({fm_date})",
                severity=IssueSeverity.INFO,
                validator="check_date_prefix_matches",
                suggestion="Update the filename or last_updated to match",
            )
        )

    return issues


# ── Public API ───────────────────────────────────────────────────


def validate_document(doc: Document) -> List[ValidationIssue]:
    """Run all validators for a document's type.

    Delegates to doc.validate_self() which uses polymorphic
    dispatch — each document subclass knows its own validators.
    """
    return doc.validate_self()
