"""BaseDocument — the core parsed document model."""

from __future__ import annotations

import re
from typing import Dict, Iterator, List, Optional, Tuple

from pydantic import BaseModel

from wos.models.enums import DocumentType, IssueSeverity
from wos.models.section import DocumentSection
from wos.models.validation_issue import ValidationIssue
from wos.models.frontmatter import (
    SECTIONS,
    SIZE_BOUNDS,
    Frontmatter,
    SectionSpec,
    SizeBounds,
)


class BaseDocument(BaseModel):
    """A complete parsed knowledge record."""

    path: str
    frontmatter: Frontmatter  # discriminated union dispatches here
    title: str
    sections: List[DocumentSection]
    raw_content: str
    frontmatter_line_end: Optional[int] = None
    title_line: Optional[int] = None

    @property
    def document_type(self) -> DocumentType:
        return DocumentType(self.frontmatter.document_type)

    @property
    def required_sections(self) -> list[SectionSpec]:
        return SECTIONS[self.document_type]

    @property
    def size_bounds(self) -> SizeBounds:
        return SIZE_BOUNDS[self.document_type]

    @property
    def section_names(self) -> list[str]:
        """Ordered list of section names."""
        return [s.name for s in self.sections]

    def get_section(self, name: str) -> Optional[DocumentSection]:
        """Get a section by name, or None if not found."""
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def get_section_content(self, name: str, default: str = "") -> str:
        """Get section content by name, or default if not found."""
        s = self.get_section(name)
        return s.content if s else default

    def has_section(self, name: str) -> bool:
        """Check if a section exists by name."""
        return any(s.name == name for s in self.sections)

    # ── String representations ─────────────────────────────────────

    def __str__(self) -> str:
        return f"{self.title} ({self.document_type.value})"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(path={self.path!r}, "
            f"type={self.document_type.value!r})"
        )

    # ── Collection protocol ────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.sections)

    def __iter__(self) -> Iterator[DocumentSection]:  # type: ignore[override]
        return iter(self.sections)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return item in self.section_names
        if isinstance(item, DocumentSection):
            return item in self.sections
        return False

    # ── Properties ─────────────────────────────────────────────────

    @property
    def area_name(self) -> Optional[str]:
        """Extract area name from context path. Returns None for non-context docs."""
        m = re.match(r"context/([^/]+)/", self.path)
        return m.group(1) if m else None

    # ── Construction ───────────────────────────────────────────────

    @classmethod
    def from_markdown(cls, path: str, content: str) -> BaseDocument:
        """Parse markdown content into a document."""
        from wos.models.parsing import parse_document

        return parse_document(path, content)

    @classmethod
    def from_json(cls, data: dict) -> BaseDocument:
        """Reconstruct a document from to_json() output.

        Requires raw_content to be present for re-parsing.
        """
        raw = data.get("raw_content", "")
        if raw:
            from wos.models.parsing import parse_document

            return parse_document(data["path"], raw)
        raise ValueError("Cannot reconstruct document without raw_content")

    # ── Representations ────────────────────────────────────────────

    def to_index_record(self) -> dict:
        """Compact record for scanning/indexing (path, type, title, description)."""
        return {
            "path": self.path,
            "document_type": self.document_type.value,
            "title": self.title,
            "description": self.frontmatter.description,
        }

    def to_outline(self) -> str:
        """Section headings with word counts — for quick orientation."""
        lines = [f"# {self.title} ({self.document_type.value})"]
        for s in self.sections:
            lines.append(f"## {s.name} ({s.word_count} words)")
        return "\n".join(lines)

    def to_plain_text(self) -> str:
        """Full plain-text rendering (title + sections, no frontmatter)."""
        parts = [f"# {self.title}"]
        for s in self.sections:
            parts.append(f"## {s.name}\n\n{s.content}")
        return "\n\n".join(parts)

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return {
            "path": self.path,
            "document_type": self.document_type.value,
            "title": self.title,
            "frontmatter": self.frontmatter.model_dump(mode="json"),
            "sections": [s.to_json() for s in self.sections],
            "raw_content": self.raw_content,
        }

    def to_markdown(self) -> str:
        """Render full document with YAML frontmatter + title + sections.

        The document knows how to serialize itself. Output should be
        re-parseable by parse_document().
        """
        fm_data = self.frontmatter.model_dump(mode="json", exclude_none=True)

        # Build frontmatter YAML manually for deterministic output
        lines = ["---"]

        # document_type first
        lines.append(f"document_type: {fm_data.pop('document_type')}")

        # description second (escaped for YAML)
        desc = fm_data.pop("description")
        lines.append(f'description: "{_escape_yaml(desc)}"')

        # Render remaining fields in a stable order
        for key in sorted(fm_data.keys()):
            value = fm_data[key]
            if key == "sources" and isinstance(value, list):
                lines.append("sources:")
                for src in value:
                    lines.append(f'  - url: "{src["url"]}"')
                    lines.append(f'    title: "{_escape_yaml(src["title"])}"')
            elif isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")

        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")

        for s in self.sections:
            lines.append("")
            lines.append(f"## {s.name}")
            lines.append("")
            lines.append(s.content)

        lines.append("")
        return "\n".join(lines)

    def get_estimated_tokens(self) -> int:
        """Estimate total token cost of this document."""
        # Title
        tokens = len(self.title) // 4 + 2
        # Frontmatter (description + metadata)
        tokens += len(self.frontmatter.description) // 4 + 10
        # Sections
        for s in self.sections:
            tokens += len(s.name) // 4 + 2  # heading
            tokens += len(s.content) // 4  # content
        return tokens

    # ── Validation ──────────────────────────────────────────────

    def validate_self(self, deep: bool = False) -> list[ValidationIssue]:
        """Run structural validators for this document type.

        Subclasses override to add type-specific validators via
        ``super().validate_self()``. The ``deep`` parameter is accepted
        for protocol consistency but not yet used at the base level.
        """
        from wos.validators import (
            check_date_fields,
            check_directory_placement,
            check_heading_hierarchy,
            check_placeholder_comments,
            check_section_ordering,
            check_section_presence,
            check_size_bounds,
            check_title_heading,
        )

        issues: list[ValidationIssue] = []
        for validator in [
            check_section_presence,
            check_section_ordering,
            check_size_bounds,
            check_directory_placement,
            check_title_heading,
            check_heading_hierarchy,
            check_placeholder_comments,
            check_date_fields,
        ]:
            issues.extend(validator(self))
        return issues

    @property
    def is_valid(self) -> bool:
        """True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0

    def validate_content(self) -> list[ValidationIssue]:
        """Run content quality checks that require LLM review.

        Returns ValidationIssue objects with requires_llm=True.
        Subclasses override to add type-specific content checks.
        """
        issues: list[ValidationIssue] = []

        # Shared: check description quality
        desc = self.frontmatter.description
        if len(desc) < 20:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="Description may be too short for agents to assess relevance",
                    severity=IssueSeverity.INFO,
                    validator="validate_content",
                    suggestion="Expand the description to be more informative",
                    requires_llm=True,
                )
            )

        return issues

    # ── Auto-fix ─────────────────────────────────────────────────

    def auto_fix(self) -> Optional[str]:
        """Apply machine-resolvable fixes and return fixed content.

        Returns the fixed markdown string, or None if no fixes were needed.
        This is user-initiated -- never called on construction.
        """
        issues = self.validate_self()
        if not issues:
            return None

        content = self.raw_content
        any_fixed = False

        for issue in issues:
            fix_fn = self._AUTO_FIX_HANDLERS.get(issue.validator)
            if not fix_fn:
                continue
            result = fix_fn(self, content, issue)
            if result is not None:
                content = result
                any_fixed = True

        if not any_fixed:
            return None

        # Validate the fixed content by re-parsing
        try:
            from wos.models.parsing import parse_document

            parse_document(self.path, content)
        except Exception:
            return None  # Fix produced invalid content, abort

        return content

    def _fix_section_ordering(
        self, content: str, issue: ValidationIssue
    ) -> Optional[str]:
        """Reorder H2 sections to canonical order."""
        canonical_order = [s.name for s in self.required_sections]
        if not canonical_order:
            return None

        # Split content into frontmatter + body
        fm_match = re.match(r"\A---\s*\n.*?\n---\s*\n", content, re.DOTALL)
        if not fm_match:
            return None

        body = content[fm_match.end():]

        # Extract title (everything before first H2)
        first_h2 = re.search(r"^##\s+", body, re.MULTILINE)
        if not first_h2:
            return None

        title_part = body[:first_h2.start()]

        # Parse sections by H2 headings
        h2_re = re.compile(r"^(##\s+.+)$", re.MULTILINE)
        h2_matches = list(h2_re.finditer(body))
        if len(h2_matches) < 2:
            return None

        sections: List[Tuple[str, str]] = []
        for i, m in enumerate(h2_matches):
            name = m.group(1).replace("## ", "").strip()
            start = m.start()
            end = (
                h2_matches[i + 1].start()
                if i + 1 < len(h2_matches)
                else len(body)
            )
            sections.append((name, body[start:end]))

        # Sort: canonical sections first (in order), then extras
        canonical_set = set(canonical_order)
        canonical_sections = []
        extra_sections = []
        for name, text in sections:
            if name in canonical_set:
                canonical_sections.append((name, text))
            else:
                extra_sections.append((name, text))

        canonical_sections.sort(
            key=lambda x: canonical_order.index(x[0])
        )

        reordered = canonical_sections + extra_sections
        reordered_body = title_part + "".join(
            text for _, text in reordered
        )

        fixed = content[:fm_match.end()] + reordered_body

        # Normalize trailing newline
        if not fixed.endswith("\n"):
            fixed += "\n"

        return fixed

    def _fix_missing_section(
        self, content: str, issue: ValidationIssue
    ) -> Optional[str]:
        """Add missing required section with TODO placeholder."""
        section_name = issue.section
        if not section_name:
            return None

        canonical_order = [s.name for s in self.required_sections]
        if section_name not in canonical_order:
            return None

        target_idx = canonical_order.index(section_name)

        lower = section_name.lower()
        new_section = (
            f"\n## {section_name}\n\n"
            f"<!-- TODO: Add {lower} content -->\n"
        )

        if target_idx == 0:
            # Insert after title (first H1)
            h1_match = re.search(r"^#\s+.+$", content, re.MULTILINE)
            if not h1_match:
                return None
            insert_pos = h1_match.end()
            fixed = (
                content[:insert_pos] + "\n" + new_section
                + content[insert_pos:]
            )
        else:
            # Insert after the preceding canonical section (or at the end)
            preceding = None
            for i in range(target_idx - 1, -1, -1):
                if self.has_section(canonical_order[i]):
                    preceding = canonical_order[i]
                    break

            if preceding:
                pattern = rf"^##\s+{re.escape(preceding)}\b"
                match = re.search(pattern, content, re.MULTILINE)
                if not match:
                    return None

                after_match = content[match.end():]
                next_h2 = re.search(r"^##\s+", after_match, re.MULTILINE)
                if next_h2:
                    insert_pos = match.end() + next_h2.start()
                else:
                    insert_pos = len(content.rstrip()) + 1
                fixed = (
                    content[:insert_pos] + new_section + "\n"
                    + content[insert_pos:]
                )
            else:
                # No preceding section exists -- insert after title
                h1_match = re.search(r"^#\s+.+$", content, re.MULTILINE)
                if not h1_match:
                    return None
                insert_pos = h1_match.end()
                fixed = (
                    content[:insert_pos] + "\n" + new_section
                    + content[insert_pos:]
                )

        return fixed

    _AUTO_FIX_HANDLERS: Dict[str, object] = {
        "check_section_ordering": _fix_section_ordering,
        "check_section_presence": _fix_missing_section,
    }


def _escape_yaml(s: str) -> str:
    """Escape characters that would break YAML double-quoted strings."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


# Backward compat alias — callers that import Document still work
Document = BaseDocument
