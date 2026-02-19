"""Per-file validators with type-dispatched routing.

Each validator function takes a Document and returns list[dict] with keys:
  file, issue, severity, validator, section, suggestion

VALIDATORS_BY_TYPE is the dispatch table — adding a new document type
means adding entries here. No validator code changes needed.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

from wos.document_types import (
    DIRECTORY_PATTERNS,
    FRESHNESS_TRACKED_TYPES,
    SECTIONS,
    Document,
    DocumentType,
)

# ── Issue factory ────────────────────────────────────────────────

Issue = Dict[str, Optional[str]]
ValidatorFn = Callable[[Document], List[Issue]]


def _issue(
    doc: Document,
    issue: str,
    severity: str,
    validator: str,
    *,
    section: Optional[str] = None,
    suggestion: Optional[str] = None,
) -> Issue:
    return {
        "file": doc.path,
        "issue": issue,
        "severity": severity,
        "validator": validator,
        "section": section,
        "suggestion": suggestion,
    }


# ── Shared validators (all types) ───────────────────────────────


def _format_section_list(doc_type: DocumentType) -> str:
    """Format the canonical section list for a document type."""
    names = [f"## {s.name}" for s in SECTIONS[doc_type]]
    prefix = f"{doc_type.value.capitalize()} documents require"
    return f"{prefix} these sections in order: {', '.join(names)}"


def check_section_presence(doc: Document) -> List[Issue]:
    """Check that all required sections exist."""
    issues: List[Issue] = []
    required = doc.required_sections
    section_hint = _format_section_list(doc.document_type)
    for spec in required:
        if spec.name not in doc.sections:
            issues.append(
                _issue(
                    doc,
                    f"Missing required section: ## {spec.name}",
                    "warn",
                    "check_section_presence",
                    section=spec.name,
                    suggestion=f"Add a ## {spec.name} section. {section_hint}",
                )
            )
    return issues


def check_section_ordering(doc: Document) -> List[Issue]:
    """Check that sections appear in canonical order."""
    issues: List[Issue] = []
    required = doc.required_sections
    section_names = list(doc.sections.keys())

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
                _issue(
                    doc,
                    f"Section ## {present[i + 1].name} appears before "
                    f"## {present[i].name} (expected after)",
                    "warn",
                    "check_section_ordering",
                    suggestion="Reorder sections to match "
                    f"canonical order. {section_hint}",
                )
            )
            break  # Report first misordering only

    return issues


def check_size_bounds(doc: Document) -> List[Issue]:
    """Check document size against bounds."""
    issues: List[Issue] = []
    bounds = doc.size_bounds
    lines = doc.raw_content.count("\n") + 1

    if lines < bounds.min_lines:
        issues.append(
            _issue(
                doc,
                f"Document is {lines} lines, minimum is {bounds.min_lines}",
                "warn",
                "check_size_bounds",
                suggestion="Add more content to meet minimum size",
            )
        )

    if bounds.max_lines and lines > bounds.max_lines:
        issues.append(
            _issue(
                doc,
                f"Document is {lines} lines, maximum is {bounds.max_lines}",
                "warn",
                "check_size_bounds",
                suggestion="Consider splitting into smaller documents",
            )
        )

    return issues


def check_directory_placement(doc: Document) -> List[Issue]:
    """Check that the file path matches expected directory pattern."""
    issues: List[Issue] = []
    pattern = DIRECTORY_PATTERNS.get(doc.document_type)
    if pattern and not re.search(pattern, doc.path):
        issues.append(
            _issue(
                doc,
                f"File path does not match expected pattern for "
                f"{doc.document_type.value}: {pattern}",
                "warn",
                "check_directory_placement",
                suggestion="Move file to the correct directory",
            )
        )
    return issues


def check_title_heading(doc: Document) -> List[Issue]:
    """Check that an H1 title exists."""
    issues: List[Issue] = []
    if not doc.title:
        issues.append(
            _issue(
                doc,
                "No H1 title heading found",
                "warn",
                "check_title_heading",
                suggestion="Add a # Title heading after the frontmatter",
            )
        )
    return issues


def check_heading_hierarchy(doc: Document) -> List[Issue]:
    """Check that heading levels don't skip (e.g., H1 -> H3)."""
    issues: List[Issue] = []
    heading_re = re.compile(r"^(#{1,6})\s+", re.MULTILINE)
    levels = [len(m.group(1)) for m in heading_re.finditer(doc.raw_content)]

    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            issues.append(
                _issue(
                    doc,
                    f"Heading level skips from H{levels[i - 1]} to "
                    f"H{levels[i]}",
                    "info",
                    "check_heading_hierarchy",
                    suggestion="Use sequential heading levels",
                )
            )
            break

    return issues


def check_placeholder_comments(doc: Document) -> List[Issue]:
    """Check for TODO/FIXME HTML comments that indicate incomplete content."""
    issues: List[Issue] = []
    placeholder_re = re.compile(
        r"<!--\s*(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE
    )
    matches = placeholder_re.findall(doc.raw_content)
    if matches:
        issues.append(
            _issue(
                doc,
                f"Found {len(matches)} placeholder comment(s): "
                f"{', '.join(set(m.upper() for m in matches))}",
                "info",
                "check_placeholder_comments",
                suggestion="Replace placeholder comments with real content",
            )
        )
    return issues


def check_date_fields(doc: Document) -> List[Issue]:
    """Check date field consistency."""
    issues: List[Issue] = []
    fm = doc.frontmatter

    # Check last_validated vs last_updated (if both exist)
    if hasattr(fm, "last_validated") and fm.last_validated:
        if fm.last_validated > fm.last_updated:
            issues.append(
                _issue(
                    doc,
                    "last_validated is after last_updated",
                    "warn",
                    "check_date_fields",
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


def check_last_validated(doc: Document) -> List[Issue]:
    """Check staleness of last_validated date.

    Only applicable to FRESHNESS_TRACKED_TYPES (topic, overview).
    Research and plan documents are NOT checked.
    """
    issues: List[Issue] = []
    if doc.document_type not in FRESHNESS_TRACKED_TYPES:
        return issues

    fm = doc.frontmatter
    if not hasattr(fm, "last_validated") or not fm.last_validated:
        return issues

    age = (date.today() - fm.last_validated).days

    if age >= _STALE_FAIL_DAYS:
        issues.append(
            _issue(
                doc,
                f"Last validated {age} days ago (threshold: {_STALE_FAIL_DAYS}d)",
                "warn",
                "check_last_validated",
                suggestion="Review and revalidate this document",
            )
        )
    elif age >= _STALE_WARN_DAYS:
        issues.append(
            _issue(
                doc,
                f"Last validated {age} days ago (threshold: {_STALE_WARN_DAYS}d)",
                "warn",
                "check_last_validated",
                suggestion="Consider reviewing this document for currency",
            )
        )
    elif age >= _STALE_INFO_DAYS:
        issues.append(
            _issue(
                doc,
                f"Last validated {age} days ago (threshold: {_STALE_INFO_DAYS}d)",
                "info",
                "check_last_validated",
                suggestion="Document is getting stale",
            )
        )

    return issues


def check_source_diversity(doc: Document) -> List[Issue]:
    """Check that sources come from multiple domains."""
    issues: List[Issue] = []
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
            _issue(
                doc,
                f"All {len(fm.sources)} sources come from the same domain",
                "info",
                "check_source_diversity",
                suggestion="Add sources from different domains for diversity",
            )
        )

    return issues


def check_go_deeper_links(doc: Document) -> List[Issue]:
    """Check that the Go Deeper section contains links (topic only)."""
    issues: List[Issue] = []
    if doc.document_type != DocumentType.TOPIC:
        return issues

    go_deeper = doc.sections.get("Go Deeper", "")
    if go_deeper and not re.search(r"\[.+\]\(.+\)", go_deeper):
        issues.append(
            _issue(
                doc,
                "Go Deeper section has no links",
                "info",
                "check_go_deeper_links",
                section="Go Deeper",
                suggestion="Add links to further reading",
            )
        )

    return issues


def check_what_this_covers_length(doc: Document) -> List[Issue]:
    """Check that the What This Covers section meets minimum word count."""
    issues: List[Issue] = []
    if doc.document_type != DocumentType.OVERVIEW:
        return issues

    section = doc.sections.get("What This Covers", "")
    word_count = len(section.split())
    min_words = 30  # From SectionSpec

    if section and word_count < min_words:
        issues.append(
            _issue(
                doc,
                f"What This Covers has {word_count} words "
                f"(minimum: {min_words})",
                "warn",
                "check_what_this_covers_length",
                section="What This Covers",
                suggestion="Expand the section description",
            )
        )

    return issues


def check_question_nonempty(doc: Document) -> List[Issue]:
    """Check that research Question section is not empty."""
    issues: List[Issue] = []
    if doc.document_type != DocumentType.RESEARCH:
        return issues

    question = doc.sections.get("Question", "")
    if not question.strip():
        issues.append(
            _issue(
                doc,
                "Question section is empty",
                "fail",
                "check_question_nonempty",
                section="Question",
                suggestion="State the research question clearly",
            )
        )

    return issues


def check_date_prefix_matches(doc: Document) -> List[Issue]:
    """Check that filename date prefix matches frontmatter last_updated."""
    issues: List[Issue] = []
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
            _issue(
                doc,
                f"Filename date ({filename_date}) differs from "
                f"last_updated ({fm_date})",
                "info",
                "check_date_prefix_matches",
                suggestion="Update the filename or last_updated to match",
            )
        )

    return issues


# ── Dispatch table ───────────────────────────────────────────────

_SHARED_VALIDATORS: List[ValidatorFn] = [
    check_section_presence,
    check_section_ordering,
    check_size_bounds,
    check_directory_placement,
    check_title_heading,
    check_heading_hierarchy,
    check_placeholder_comments,
    check_date_fields,
]

VALIDATORS_BY_TYPE: Dict[DocumentType, List[ValidatorFn]] = {
    DocumentType.TOPIC: _SHARED_VALIDATORS + [
        check_last_validated,
        check_source_diversity,
        check_go_deeper_links,
    ],
    DocumentType.OVERVIEW: _SHARED_VALIDATORS + [
        check_last_validated,
        check_what_this_covers_length,
    ],
    DocumentType.RESEARCH: _SHARED_VALIDATORS + [
        check_source_diversity,
        check_question_nonempty,
        check_date_prefix_matches,
    ],
    DocumentType.PLAN: _SHARED_VALIDATORS + [
        check_date_prefix_matches,
    ],
    DocumentType.NOTE: list(_SHARED_VALIDATORS),
}


def validate_document(doc: Document) -> List[Issue]:
    """Run all validators for a document's type."""
    validators = VALIDATORS_BY_TYPE.get(doc.document_type, _SHARED_VALIDATORS)
    issues: List[Issue] = []
    for validator in validators:
        issues.extend(validator(doc))
    return issues
