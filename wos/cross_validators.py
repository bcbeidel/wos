"""Cross-file validators that need the full document set.

These validators check relationships between documents and consistency
with external state (CLAUDE.md manifest, file system).
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from wos.discovery import MARKER_BEGIN, MARKER_END, render_manifest, scan_context
from wos.document_types import SOURCE_GROUNDED_TYPES, Document, DocumentType
from wos.source_verification import check_url_reachability

Issue = Dict[str, Optional[str]]


def _issue(
    file: str,
    issue: str,
    severity: str,
    validator: str,
    *,
    section: Optional[str] = None,
    suggestion: Optional[str] = None,
) -> Issue:
    return {
        "file": file,
        "issue": issue,
        "severity": severity,
        "validator": validator,
        "section": section,
        "suggestion": suggestion,
    }


def check_link_graph(
    docs: List[Document], root: str
) -> List[Issue]:
    """Check that all related links resolve.

    File paths must exist on disk. URLs are format-checked only.
    Broken file paths → severity: fail.
    """
    issues: List[Issue] = []
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
                        _issue(
                            doc.path,
                            f"Malformed URL in related: {link}",
                            "fail",
                            "check_link_graph",
                            suggestion="Fix the URL format",
                        )
                    )
            else:
                # File path — must exist on disk
                target = root_path / link
                if not target.exists():
                    issues.append(
                        _issue(
                            doc.path,
                            f"Broken related link: {link}",
                            "fail",
                            "check_link_graph",
                            suggestion="Fix the path or remove the link",
                        )
                    )

    return issues


def check_overview_topic_sync(
    docs: List[Document], root: str
) -> List[Issue]:
    """Check that overview Topics sections match actual topic files.

    A topic on disk that is not listed in its area's overview → fail.
    """
    issues: List[Issue] = []

    # Group by area
    overviews: Dict[str, Document] = {}
    topics_by_area: Dict[str, List[Document]] = {}

    for doc in docs:
        if doc.document_type == DocumentType.OVERVIEW:
            # Extract area from path: context/{area}/_overview.md
            match = re.match(r"context/([^/]+)/", doc.path)
            if match:
                overviews[match.group(1)] = doc
        elif doc.document_type == DocumentType.TOPIC:
            match = re.match(r"context/([^/]+)/", doc.path)
            if match:
                area = match.group(1)
                topics_by_area.setdefault(area, []).append(doc)

    for area, area_topics in topics_by_area.items():
        overview = overviews.get(area)
        if not overview:
            continue

        topics_section = overview.sections.get("Topics", "")

        for topic in area_topics:
            # Check if topic filename or title appears in the Topics section
            filename = Path(topic.path).stem
            if (
                filename not in topics_section
                and topic.title not in topics_section
            ):
                issues.append(
                    _issue(
                        overview.path,
                        f"Topic '{topic.title}' ({topic.path}) not listed "
                        f"in overview Topics section",
                        "fail",
                        "check_overview_topic_sync",
                        section="Topics",
                        suggestion=f"Add {topic.title} to the Topics section",
                    )
                )

    return issues


def check_manifest_sync(
    docs: List[Document], root: str
) -> List[Issue]:
    """Check that CLAUDE.md manifest matches disk state.

    Drift between manifest and actual files → severity: warn.
    """
    issues: List[Issue] = []
    claude_md_path = Path(root) / "CLAUDE.md"

    if not claude_md_path.exists():
        return issues

    content = claude_md_path.read_text(encoding="utf-8")
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
            _issue(
                "CLAUDE.md",
                "Manifest is out of sync with context files on disk",
                "warn",
                "check_manifest_sync",
                suggestion="Run discovery to regenerate: "
                "python3 scripts/run_discovery.py",
            )
        )

    return issues


def check_naming_conventions(
    docs: List[Document], root: str
) -> List[Issue]:
    """Check that file and directory names follow conventions."""
    issues: List[Issue] = []
    slug_re = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

    for doc in docs:
        if doc.document_type in {DocumentType.TOPIC, DocumentType.OVERVIEW}:
            # Check area directory name
            match = re.match(r"context/([^/]+)/", doc.path)
            if match:
                area_name = match.group(1)
                if not slug_re.match(area_name):
                    issues.append(
                        _issue(
                            doc.path,
                            f"Area directory '{area_name}' is not "
                            f"lowercase-hyphenated",
                            "warn",
                            "check_naming_conventions",
                            suggestion="Rename to lowercase-hyphenated format",
                        )
                    )

        if doc.document_type == DocumentType.TOPIC:
            # Check topic filename
            filename = Path(doc.path).stem
            if not slug_re.match(filename):
                issues.append(
                    _issue(
                        doc.path,
                        f"Topic filename '{filename}' is not "
                        f"lowercase-hyphenated",
                        "warn",
                        "check_naming_conventions",
                        suggestion="Rename to lowercase-hyphenated format",
                    )
                )

    return issues


def check_source_url_reachability(
    docs: List[Document], root: str
) -> List[Issue]:
    """Check that source URLs in frontmatter are reachable.

    Collects unique URLs from SOURCE_GROUNDED_TYPES documents, checks each
    once via HTTP HEAD, and maps results back to issue dicts per file.
    Rate-limited to 100ms between requests to the same domain.
    """
    issues: List[Issue] = []

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
            severity = "info"
            suggestion = (
                "Verify source is accessible. If paywalled,"
                " consider linking to an open-access mirror."
            )
        elif result.http_status == 404:
            severity = "warn"
            suggestion = (
                "Verify source still exists. If removed,"
                " find replacement or remove citation."
            )
        else:
            severity = "warn"
            suggestion = (
                "Check if source is temporarily down"
                " or permanently unavailable."
            )

        # Emit one issue per file that cites this URL
        for file_path in files:
            issues.append(
                _issue(
                    file_path,
                    f"Source URL unreachable: {url} — {result.reason}",
                    severity,
                    "check_source_url_reachability",
                    suggestion=suggestion,
                )
            )

    return issues


def run_cross_validators(
    docs: List[Document], root: str
) -> List[Issue]:
    """Run all cross-file validators."""
    issues: List[Issue] = []
    issues.extend(check_link_graph(docs, root))
    issues.extend(check_overview_topic_sync(docs, root))
    issues.extend(check_manifest_sync(docs, root))
    issues.extend(check_naming_conventions(docs, root))
    return issues


def _is_url(s: str) -> bool:
    """Check if a string looks like a URL."""
    return s.startswith("http://") or s.startswith("https://")
