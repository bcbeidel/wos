"""Per-file and project-wide validation checks.

Provides five individual checks (frontmatter, research sources, source
URLs, related paths, index sync) and two composite functions
(validate_file, validate_project) that orchestrate them.

Each check returns a list of issue dicts with keys: file, issue, severity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from wos.document import Document, parse_document
from wos.index import check_index_sync
from wos.url_checker import check_urls

# ── Individual checks ──────────────────────────────────────────


def check_frontmatter(doc: Document) -> List[dict]:
    """Check that name and description are non-empty strings.

    Args:
        doc: A parsed Document instance.

    Returns:
        List of issue dicts. Empty if valid.
    """
    issues: List[dict] = []
    if not doc.name or not doc.name.strip():
        issues.append({
            "file": doc.path,
            "issue": "Frontmatter 'name' is empty",
            "severity": "fail",
        })
    if not doc.description or not doc.description.strip():
        issues.append({
            "file": doc.path,
            "issue": "Frontmatter 'description' is empty",
            "severity": "fail",
        })
    return issues


def check_research_sources(doc: Document) -> List[dict]:
    """Check that research documents have non-empty sources.

    Non-research documents (or documents without a type) always pass.

    Args:
        doc: A parsed Document instance.

    Returns:
        List of issue dicts. Empty if valid.
    """
    if doc.type != "research":
        return []
    if not doc.sources:
        return [{
            "file": doc.path,
            "issue": "Research document has no sources",
            "severity": "fail",
        }]
    return []


def check_source_urls(doc: Document) -> List[dict]:
    """Check that all URLs in doc.sources are reachable.

    Calls check_urls() from wos.url_checker. If the document has no
    sources, the check is skipped entirely (check_urls is not called).

    Args:
        doc: A parsed Document instance.

    Returns:
        List of issue dicts. Empty if all sources are reachable.
    """
    if not doc.sources:
        return []

    results = check_urls(doc.sources)
    issues: List[dict] = []
    for result in results:
        if not result.reachable:
            reason = f" ({result.reason})" if result.reason else ""
            issues.append({
                "file": doc.path,
                "issue": f"Source URL unreachable: {result.url}{reason}",
                "severity": "fail",
            })
    return issues


def check_related_paths(doc: Document, root: Path) -> List[dict]:
    """Check that file paths in doc.related exist on disk.

    URLs (http:// or https://) are skipped — only local file paths
    are validated.

    Args:
        doc: A parsed Document instance.
        root: Project root directory for resolving relative paths.

    Returns:
        List of issue dicts. Empty if all paths exist.
    """
    issues: List[dict] = []
    for rel in doc.related:
        # Skip URLs
        if rel.startswith("http://") or rel.startswith("https://"):
            continue
        full_path = root / rel
        if not full_path.exists():
            issues.append({
                "file": doc.path,
                "issue": f"Related path does not exist: {rel}",
                "severity": "fail",
            })
    return issues


def check_all_indexes(directory: Path) -> List[dict]:
    """Recursively check all _index.md files under a directory.

    Walks all subdirectories and runs check_index_sync() on each.

    Args:
        directory: Root directory to walk.

    Returns:
        List of issue dicts from all index checks.
    """
    issues: List[dict] = []
    if not directory.is_dir():
        return issues

    # Check the directory itself
    issues.extend(check_index_sync(directory))

    # Recurse into subdirectories
    for entry in sorted(directory.iterdir()):
        if entry.is_dir():
            issues.extend(check_all_indexes(entry))

    return issues


# ── Composite functions ────────────────────────────────────────


def validate_file(
    path: Path, root: Path, check_urls: bool = True
) -> List[dict]:
    """Validate a single markdown file.

    Reads the file, parses it with parse_document(), then runs
    checks 1-4 (frontmatter, research sources, source URLs, related
    paths). If parsing fails, returns a single parse-error issue.

    Args:
        path: Path to the .md file.
        root: Project root directory.
        check_urls: If False, skip source URL reachability check.

    Returns:
        List of issue dicts.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [{
            "file": str(path),
            "issue": f"Cannot read file: {exc}",
            "severity": "fail",
        }]

    try:
        doc = parse_document(str(path), text)
    except ValueError as exc:
        return [{
            "file": str(path),
            "issue": f"Parse error: {exc}",
            "severity": "fail",
        }]

    issues: List[dict] = []
    issues.extend(check_frontmatter(doc))
    issues.extend(check_research_sources(doc))
    if check_urls:
        issues.extend(check_source_urls(doc))
    issues.extend(check_related_paths(doc, root))
    return issues


def validate_project(
    root: Path, check_urls: bool = True
) -> List[dict]:
    """Validate all markdown files in a project.

    Walks context/ and artifacts/ directories under root. Runs index
    sync checks on each directory, and per-file checks on each .md
    file (excluding _index.md files).

    Args:
        root: Project root directory.
        check_urls: If False, skip source URL reachability checks.

    Returns:
        List of all issue dicts found.
    """
    issues: List[dict] = []

    for subdir_name in ("context", "artifacts"):
        subdir = root / subdir_name
        if not subdir.is_dir():
            continue

        # Index sync checks (recursive)
        issues.extend(check_all_indexes(subdir))

        # Per-file checks on all .md files (excluding _index.md)
        for dirpath, _dirnames, filenames in os.walk(subdir):
            for filename in sorted(filenames):
                if filename == "_index.md":
                    continue
                if not filename.endswith(".md"):
                    continue
                file_path = Path(dirpath) / filename
                issues.extend(validate_file(file_path, root, check_urls=check_urls))

    return issues
