"""Document dataclass and frontmatter parser.

Provides a single Document dataclass representing any WOS document
(topic, overview, research, plan) and a parse_document() function
that extracts YAML frontmatter into structured fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from wos.frontmatter import parse_frontmatter
from wos.suffix import type_from_path


@dataclass
class Document:
    """A parsed WOS document with frontmatter metadata and body content."""

    path: str
    name: str
    description: str
    content: str
    type: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    status: Optional[str] = None
    meta: dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        """Number of words in body content."""
        return len(self.content.split())

    def has_section(self, keyword: str) -> bool:
        """Return True if any heading line contains keyword (case-insensitive)."""
        for line in self.content.splitlines():
            stripped = line.strip()
            heading_text = stripped.lstrip("#").strip().lower()
            if stripped.startswith("#") and keyword in heading_text:
                return True
        return False

    def issues(self, root: Path) -> List[dict]:
        """Return validation issues common to all documents.

        Checks that name and description are non-empty, and that all
        local file paths in ``related`` exist on disk.

        Args:
            root: Project root directory for resolving relative paths.

        Returns:
            List of issue dicts with keys: file, issue, severity.
        """
        result: List[dict] = []

        if not self.name or not self.name.strip():
            result.append({
                "file": self.path,
                "issue": "Frontmatter 'name' is empty",
                "severity": "fail",
            })
        if not self.description or not self.description.strip():
            result.append({
                "file": self.path,
                "issue": "Frontmatter 'description' is empty",
                "severity": "fail",
            })

        for rel in self.related:
            if rel.startswith("http://") or rel.startswith("https://"):
                continue
            if not (root / rel).exists():
                result.append({
                    "file": self.path,
                    "issue": f"Related path does not exist: {rel}",
                    "severity": "fail",
                })

        return result

    def is_valid(self, root: Path) -> bool:
        """Return True if issues() contains no fail-severity entries.

        Args:
            root: Project root directory.

        Returns:
            True if the document has no fail-severity issues.
        """
        return not any(i["severity"] == "fail" for i in self.issues(root))


def parse_document(path: str, text: str) -> Document:
    """Parse a markdown document with YAML frontmatter.

    Extracts frontmatter between ``---`` delimiters. Known fields
    (name, description, type, sources, related) become Document
    attributes; unknown fields are collected in ``meta``.

    Args:
        path: File path for the document.
        text: Raw markdown text including frontmatter.

    Returns:
        A Document instance with parsed metadata and body content.

    Raises:
        ValueError: If frontmatter is missing, or required fields
            (name, description) are absent.
    """
    try:
        fm, content = parse_frontmatter(text)
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc

    # ── Validate required fields ───────────────────────────────
    if "name" not in fm:
        raise ValueError(f"{path}: frontmatter missing required field 'name'")
    if "description" not in fm:
        raise ValueError(
            f"{path}: frontmatter missing required field 'description'"
        )

    # ── Extract known fields ───────────────────────────────────
    name: str = str(fm["name"]) if fm["name"] is not None else ""
    description: str = str(fm["description"]) if fm["description"] is not None else ""
    doc_type: Optional[str] = fm.get("type")
    if not isinstance(doc_type, str) and doc_type is not None:
        doc_type = str(doc_type)
    if doc_type is None:
        doc_type = type_from_path(Path(path))
    sources: List[str] = fm.get("sources") or []
    related: List[str] = fm.get("related") or []
    status: Optional[str] = fm.get("status")
    if not isinstance(status, str) and status is not None:
        status = str(status)

    _VALID_STATUSES = {"draft", "approved", "executing", "completed", "abandoned"}
    if status is not None and status not in _VALID_STATUSES:
        raise ValueError(
            f"{path}: invalid status '{status}', "
            f"must be one of: {', '.join(sorted(_VALID_STATUSES))}"
        )

    _KNOWN_KEYS = {"name", "description", "type", "sources", "related", "status"}
    meta = {k: v for k, v in fm.items() if k not in _KNOWN_KEYS}

    return Document(
        path=path,
        name=name,
        description=description,
        content=content,
        type=doc_type,
        sources=sources,
        related=related,
        status=status,
        meta=meta,
    )
