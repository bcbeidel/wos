"""Per-file and project-wide validation checks.

Provides content length check, index sync, project-file checks, and two
composite functions (validate_file, validate_project) that orchestrate
them. Document-level validation (frontmatter, sources, URLs, related
paths) now lives on the document subclasses via doc.issues(root).

Each check returns a list of issue dicts with keys: file, issue, severity.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from wos.document import Document, ResearchDocument, parse_document
from wos.index import check_index_sync, extract_preamble


def check_content(
    doc: Document,
    max_words: int = 800,
    min_words: int = 100,
) -> List[dict]:
    """Warn when context-type files exceed or fall below word count thresholds.

    Only checks documents with type ``context``. Non-context files and
    _index.md files are excluded.

    Args:
        doc: A parsed Document instance.
        max_words: Upper word count threshold (default 800).
        min_words: Lower word count threshold (default 100).

    Returns:
        List of issue dicts. Empty if within thresholds.
    """
    if doc.type != "context":
        return []
    if doc.path.endswith("_index.md"):
        return []

    word_count = doc.word_count
    if word_count > max_words:
        return [{
            "file": doc.path,
            "issue": f"Context file is {word_count} words (threshold: {max_words})",
            "severity": "warn",
        }]
    if word_count < min_words:
        return [{
            "file": doc.path,
            "issue": f"Context file is {word_count} words (minimum: {min_words})",
            "severity": "warn",
        }]
    return []


def check_all_indexes(directory: Path) -> List[dict]:
    """Recursively check all _index.md files under a directory.

    Walks all subdirectories and runs check_index_sync() on each.
    Also warns when an _index.md exists but has no preamble.

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

    # WARN: index exists but has no preamble (area description)
    index_path = directory / "_index.md"
    if index_path.is_file() and extract_preamble(index_path) is None:
        issues.append({
            "file": str(index_path),
            "issue": "Index has no area description (preamble)",
            "severity": "warn",
        })

    # Recurse into subdirectories
    for entry in sorted(directory.iterdir()):
        if entry.is_dir():
            issues.extend(check_all_indexes(entry))

    return issues


# ── Composite functions ────────────────────────────────────────


def validate_file(
    path: Path,
    root: Path,
    verify_urls: bool = True,
    context_max_words: int = 800,
    context_min_words: int = 100,
) -> List[dict]:
    """Validate a single markdown file.

    Reads the file, parses it with parse_document(), then calls
    doc.issues(root) (type-dispatched) plus content-length check.
    If parsing fails, returns a single parse-error issue.

    Args:
        path: Path to the .md file.
        root: Project root directory.
        verify_urls: If False, skip source URL reachability check.
        context_max_words: Upper word count threshold for context files.
        context_min_words: Lower word count threshold for context files.

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

    if isinstance(doc, ResearchDocument):
        issues.extend(doc.issues(root, verify_urls=verify_urls))
    else:
        issues.extend(doc.issues(root))

    # Context-file warning: no ContextDocument subclass, so inline here
    if doc.type == "context" and not doc.related:
        issues.append({
            "file": doc.path,
            "issue": "Context file has no related fields",
            "severity": "warn",
        })

    issues.extend(check_content(
        doc, max_words=context_max_words, min_words=context_min_words,
    ))
    return issues


def check_project_files(root: Path) -> List[dict]:
    """Warn when AGENTS.md or CLAUDE.md are missing or misconfigured.

    Checks:
    - AGENTS.md missing
    - AGENTS.md exists but lacks ``<!-- wos:begin -->`` marker
    - CLAUDE.md missing
    - CLAUDE.md exists but doesn't reference ``@AGENTS.md``

    Args:
        root: Project root directory.

    Returns:
        List of issue dicts. Empty if all checks pass.
    """
    issues: List[dict] = []

    agents_path = root / "AGENTS.md"
    if not agents_path.is_file():
        issues.append({
            "file": "AGENTS.md",
            "issue": "No AGENTS.md found. Run /wos:setup to initialize.",
            "severity": "warn",
        })
    else:
        try:
            content = agents_path.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "<!-- wos:begin -->" not in content:
            issues.append({
                "file": "AGENTS.md",
                "issue": "AGENTS.md lacks WOS markers. Navigation updates won't work.",
                "severity": "warn",
            })

    claude_path = root / "CLAUDE.md"
    if not claude_path.is_file():
        issues.append({
            "file": "CLAUDE.md",
            "issue": "No CLAUDE.md found. Run /wos:setup to initialize.",
            "severity": "warn",
        })
    else:
        try:
            content = claude_path.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if "@AGENTS.md" not in content:
            issues.append({
                "file": "CLAUDE.md",
                "issue": (
                    "CLAUDE.md doesn't reference @AGENTS.md."
                    " Navigation may not load."
                ),
                "severity": "warn",
            })

    return issues


def validate_project(
    root: Path,
    verify_urls: bool = True,
    context_max_words: int = 800,
    context_min_words: int = 100,
    exclude_dirs: Optional[frozenset] = None,
) -> List[dict]:
    """Validate all managed documents in a project.

    Discovers documents by walking the project tree and checking for
    valid frontmatter. Runs index sync checks on directories containing
    managed documents. Also checks project-level files (AGENTS.md,
    CLAUDE.md).

    Args:
        root: Project root directory.
        verify_urls: If False, skip source URL reachability checks.
        exclude_dirs: Top-level directory names to exclude from index
            checks. Defaults to INDEX_EXCLUDED_DIRS. Pass frozenset()
            to include all.

    Returns:
        List of all issue dicts found.
    """
    from wos.discovery import discover_document_dirs, discover_documents

    issues: List[dict] = []

    # Project-level checks
    issues.extend(check_project_files(root))

    # Discover and validate all managed documents
    documents = discover_documents(root)
    for doc in documents:
        if isinstance(doc, ResearchDocument):
            issues.extend(doc.issues(root, verify_urls=verify_urls))
        else:
            issues.extend(doc.issues(root))

        # Context-file warning: no ContextDocument subclass, so inline here
        if doc.type == "context" and not doc.related:
            issues.append({
                "file": doc.path,
                "issue": "Context file has no related fields",
                "severity": "warn",
            })

        issues.extend(check_content(
            doc, max_words=context_max_words, min_words=context_min_words,
        ))

    # Index sync checks on directories containing managed documents
    doc_dirs = discover_document_dirs(root, exclude_dirs=exclude_dirs)
    for directory in doc_dirs:
        issues.extend(check_all_indexes(directory))

    return issues
