"""Cross-file validators that need the full document set.

These validators check relationships between documents and consistency
with external state (AGENTS.md manifest, file system).
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

from wos.discovery import MARKER_BEGIN, MARKER_END, render_manifest, scan_context
from wos.document_types import (
    SOURCE_GROUNDED_TYPES,
    ContextArea,
    Document,
    DocumentType,
    IssueSeverity,
    ValidationIssue,
)
from wos.source_verification import check_url_reachability


def check_link_graph(
    docs: List[Document], root: str
) -> List[ValidationIssue]:
    """Check that all related links resolve.

    File paths must exist on disk. URLs are format-checked only.
    Broken file paths -> severity: fail.
    """
    issues: List[ValidationIssue] = []
    root_path = Path(root)

    for doc in docs:
        related = doc.frontmatter.related
        if not related:
            continue

        for link in related:
            if _is_url(link):
                # Format check only
                parsed = urlparse(link)
                if not parsed.scheme or not parsed.netloc:
                    issues.append(
                        ValidationIssue(
                            file=doc.path,
                            issue=f"Malformed URL in related: {link}",
                            severity=IssueSeverity.FAIL,
                            validator="check_link_graph",
                            suggestion="Fix the URL format",
                        )
                    )
            else:
                # File path — must exist on disk
                target = root_path / link
                if not target.exists():
                    issues.append(
                        ValidationIssue(
                            file=doc.path,
                            issue=f"Broken related link: {link}",
                            severity=IssueSeverity.FAIL,
                            validator="check_link_graph",
                            suggestion="Fix the path or remove the link",
                        )
                    )

    return issues


def check_overview_topic_sync(
    docs: List[Document], root: str
) -> List[ValidationIssue]:
    """Check that overview Topics sections match actual topic files.

    A topic on disk that is not listed in its area's overview -> fail.
    Delegates to ContextArea.validate() for the overview-topic sync check.
    """
    areas = _build_context_areas(docs)
    issues: List[ValidationIssue] = []
    for area in areas:
        issues.extend(area._check_overview_topic_sync())
    return issues


def check_manifest_sync(
    docs: List[Document], root: str
) -> List[ValidationIssue]:
    """Check that AGENTS.md manifest matches disk state.

    Drift between manifest and actual files -> severity: warn.
    """
    issues: List[ValidationIssue] = []
    agents_md_path = Path(root) / "AGENTS.md"

    if not agents_md_path.exists():
        return issues

    content = agents_md_path.read_text(encoding="utf-8")
    begin_idx = content.find(MARKER_BEGIN)
    end_idx = content.find(MARKER_END)

    if begin_idx == -1 or end_idx == -1:
        return issues

    current_manifest = content[begin_idx + len(MARKER_BEGIN):end_idx].strip()

    # Generate what the manifest should be
    areas = scan_context(root)
    expected_manifest = render_manifest(areas).strip()

    if current_manifest != expected_manifest:
        issues.append(
            ValidationIssue(
                file="AGENTS.md",
                issue="Manifest is out of sync with context files on disk",
                severity=IssueSeverity.WARN,
                validator="check_manifest_sync",
                suggestion="Run discovery to regenerate: "
                "python3 scripts/run_discovery.py",
            )
        )

    return issues


def check_naming_conventions(
    docs: List[Document], root: str
) -> List[ValidationIssue]:
    """Check that file and directory names follow conventions.

    Delegates to ContextArea.validate() for context docs.
    Non-context docs (notes, etc.) are skipped.
    """
    areas = _build_context_areas(docs)
    issues: List[ValidationIssue] = []
    for area in areas:
        issues.extend(area._check_naming_conventions())
    return issues


def check_source_url_reachability(
    docs: List[Document], root: str
) -> List[ValidationIssue]:
    """Check that source URLs in frontmatter are reachable.

    Collects unique URLs from SOURCE_GROUNDED_TYPES documents, checks each
    once via HTTP HEAD, and maps results back to issues per file.
    Rate-limited to 100ms between requests to the same domain.
    """
    issues: List[ValidationIssue] = []

    # Collect unique URLs and map back to files
    url_to_files: Dict[str, List[str]] = {}
    for doc in docs:
        if doc.document_type not in SOURCE_GROUNDED_TYPES:
            continue
        sources = getattr(doc.frontmatter, "sources", None)
        if not sources:
            continue
        for source in sources:
            url_to_files.setdefault(source.url, []).append(doc.path)

    # Check each unique URL once, with per-domain rate limiting
    last_request_by_domain: Dict[str, float] = {}

    for url, files in url_to_files.items():
        domain = urlparse(url).netloc

        # Rate limit: 100ms between requests to same domain
        last = last_request_by_domain.get(domain, 0.0)
        elapsed = time.monotonic() - last
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)

        result = check_url_reachability(url)
        last_request_by_domain[domain] = time.monotonic()

        if result.reachable:
            continue

        # Map severity based on HTTP status
        if result.http_status == 403:
            severity = IssueSeverity.INFO
            suggestion = (
                "Verify source is accessible. If paywalled,"
                " consider linking to an open-access mirror."
            )
        elif result.http_status == 404:
            severity = IssueSeverity.WARN
            suggestion = (
                "Verify source still exists. If removed,"
                " find replacement or remove citation."
            )
        else:
            severity = IssueSeverity.WARN
            suggestion = (
                "Check if source is temporarily down"
                " or permanently unavailable."
            )

        # Emit one issue per file that cites this URL
        for file_path in files:
            issues.append(
                ValidationIssue(
                    file=file_path,
                    issue=f"Source URL unreachable: {url} — {result.reason}",
                    severity=severity,
                    validator="check_source_url_reachability",
                    suggestion=suggestion,
                )
            )

    return issues


def _build_context_areas(docs: List[Document]) -> List[ContextArea]:
    """Group parsed documents into ContextArea objects by area directory.

    Only includes context-type docs (topic, overview). Used by
    check_overview_topic_sync and check_naming_conventions.
    """
    area_map: Dict[str, ContextArea] = {}

    for doc in docs:
        if doc.document_type not in {DocumentType.TOPIC, DocumentType.OVERVIEW}:
            continue

        match = re.match(r"context/([^/]+)/", doc.path)
        if not match:
            continue

        area_name = match.group(1)
        if area_name not in area_map:
            area_map[area_name] = ContextArea(name=area_name)

        area = area_map[area_name]
        if doc.document_type == DocumentType.OVERVIEW:
            area.overview = doc
        elif doc.document_type == DocumentType.TOPIC:
            area.topics.append(doc)

    return list(area_map.values())


def run_cross_validators(
    docs: List[Document], root: str
) -> List[ValidationIssue]:
    """Run all cross-file validators."""
    issues: List[ValidationIssue] = []
    issues.extend(check_link_graph(docs, root))
    issues.extend(check_overview_topic_sync(docs, root))
    issues.extend(check_manifest_sync(docs, root))
    issues.extend(check_naming_conventions(docs, root))
    return issues


def _is_url(s: str) -> bool:
    """Check if a string looks like a URL."""
    return s.startswith("http://") or s.startswith("https://")
