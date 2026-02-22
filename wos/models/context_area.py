"""ContextArea model — a context area with its documents.

Consolidates the former AreaInfo/TopicInfo dataclasses from discovery.py.
Each ContextArea represents a directory under /context/ with an optional
overview document and zero or more topic documents.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from wos.models.core import DocumentType, IssueSeverity, ValidationIssue


class ContextArea(BaseModel):
    """A context area (directory under /context/) with its documents."""

    name: str  # directory name, e.g. "python"
    overview: Optional["OverviewDocument"] = None  # noqa: F821
    topics: List["TopicDocument"] = []  # noqa: F821

    @property
    def display_name(self) -> str:
        """Title-cased display name. 'python-basics' -> 'Python Basics'."""
        return self.name.replace("-", " ").title()

    @property
    def overview_path(self) -> Optional[str]:
        """Root-relative path to _overview.md, or None."""
        return self.overview.path if self.overview else None

    @property
    def overview_description(self) -> Optional[str]:
        """Description from overview frontmatter, or None."""
        return self.overview.frontmatter.description if self.overview else None

    # ── Construction ────────────────────────────────────────────

    @classmethod
    def from_documents(cls, docs: list) -> List[ContextArea]:
        """Group parsed documents into ContextArea objects by area directory."""
        area_map: dict[str, ContextArea] = {}
        for doc in docs:
            if doc.document_type not in {DocumentType.TOPIC, DocumentType.OVERVIEW}:
                continue
            area_name = doc.area_name
            if not area_name:
                continue
            if area_name not in area_map:
                area_map[area_name] = cls(name=area_name)
            area = area_map[area_name]
            if doc.document_type == DocumentType.OVERVIEW:
                area.overview = doc
            elif doc.document_type == DocumentType.TOPIC:
                area.topics.append(doc)
        return sorted(area_map.values(), key=lambda a: a.name)

    @classmethod
    def from_directory(cls, root: str, area_name: str) -> ContextArea:
        """Parse all context documents in an area directory."""
        from wos.models.parsing import parse_document

        context_dir = Path(root) / "context" / area_name
        area = cls(name=area_name)

        for md_file in sorted(context_dir.iterdir()):
            if not md_file.is_file() or md_file.suffix != ".md":
                continue

            rel_path = str(md_file.relative_to(root))
            try:
                content = md_file.read_text(encoding="utf-8")
                doc = parse_document(rel_path, content)
            except Exception:
                continue

            if doc.document_type == DocumentType.OVERVIEW:
                area.overview = doc
            elif doc.document_type == DocumentType.TOPIC:
                area.topics.append(doc)

        return area

    @classmethod
    def scan_all(cls, root: str) -> List[ContextArea]:
        """Scan all area directories under /context/ and return ContextArea list."""
        context_dir = Path(root) / "context"
        if not context_dir.is_dir():
            return []

        areas: List[ContextArea] = []
        for entry in sorted(context_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            areas.append(cls.from_directory(root, entry.name))

        return areas

    # ── Representations ─────────────────────────────────────────

    def __str__(self) -> str:
        return f"{self.display_name} ({len(self.topics)} topics)"

    def __repr__(self) -> str:
        return f"ContextArea(name={self.name!r}, topics={len(self.topics)})"

    def __len__(self) -> int:
        return len(self.topics)

    def __iter__(self):
        return iter(self.topics)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return any(t.title == item for t in self.topics)
        return item in self.topics

    def to_manifest_entry(self) -> str:
        """Single table row for the AGENTS.md manifest."""
        description = self.overview_description or ""
        if self.overview_path:
            link = f"[{self.display_name}]({self.overview_path})"
        else:
            link = f"[{self.display_name}](context/{self.name}/)"
        return f"| {link} | {description} |"

    def to_index_records(self) -> list[dict]:
        """Compact index records for all documents in this area."""
        records = []
        if self.overview:
            records.append(self.overview.to_index_record())
        for topic in self.topics:
            records.append(topic.to_index_record())
        return records

    def get_estimated_tokens(self) -> int:
        """Aggregate estimated token cost of all documents in this area."""
        total = 0
        if self.overview:
            total += self.overview.get_estimated_tokens()
        for topic in self.topics:
            total += topic.get_estimated_tokens()
        return total

    # ── Validation ──────────────────────────────────────────────

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        """Run area-level validators (overview-topic sync, naming)."""
        issues: list[ValidationIssue] = []
        issues.extend(self._check_overview_topic_sync())
        issues.extend(self._check_naming_conventions())
        return issues

    @property
    def is_valid(self) -> bool:
        """True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0

    def _check_overview_topic_sync(self) -> list[ValidationIssue]:
        """Check that overview Topics section lists all topic files."""
        if not self.overview or not self.topics:
            return []

        topics_section = self.overview.get_section_content("Topics")
        issues: list[ValidationIssue] = []

        for topic in self.topics:
            filename = Path(topic.path).stem
            if filename not in topics_section and topic.title not in topics_section:
                issues.append(
                    ValidationIssue(
                        file=self.overview.path,
                        issue=f"Topic '{topic.title}' ({topic.path}) not listed "
                              f"in overview Topics section",
                        severity=IssueSeverity.FAIL,
                        validator="check_overview_topic_sync",
                        section="Topics",
                        suggestion=f"Add {topic.title} to the Topics section",
                    )
                )

        return issues

    def _check_naming_conventions(self) -> list[ValidationIssue]:
        """Check area and topic file naming conventions."""
        issues: list[ValidationIssue] = []
        slug_re = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

        # Check area directory name
        if not slug_re.match(self.name):
            # Use first available doc path for the issue
            file_path = f"context/{self.name}/"
            if self.overview:
                file_path = self.overview.path
            elif self.topics:
                file_path = self.topics[0].path
            issues.append(
                ValidationIssue(
                    file=file_path,
                    issue=f"Area directory '{self.name}' is not "
                          f"lowercase-hyphenated",
                    severity=IssueSeverity.WARN,
                    validator="check_naming_conventions",
                    suggestion="Rename to lowercase-hyphenated format",
                )
            )

        # Check topic filenames
        for topic in self.topics:
            filename = Path(topic.path).stem
            if not slug_re.match(filename):
                issues.append(
                    ValidationIssue(
                        file=topic.path,
                        issue=f"Topic filename '{filename}' is not "
                              f"lowercase-hyphenated",
                        severity=IssueSeverity.WARN,
                        validator="check_naming_conventions",
                        suggestion="Rename to lowercase-hyphenated format",
                    )
                )

        return issues


# Resolve forward references after OverviewDocument/TopicDocument are defined
def _rebuild_model() -> None:
    from wos.models.documents import OverviewDocument, TopicDocument  # noqa: F401

    ContextArea.model_rebuild()


_rebuild_model()
