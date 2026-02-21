"""AgentsMd -- entity for the AGENTS.md file.

Owns the AGENTS.md content with context manifest between markers.
Ports marker handling, manifest rendering, and template logic from
discovery.py into a proper domain entity.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel

from wos.models.enums import IssueSeverity
from wos.models.validation_issue import ValidationIssue

MARKER_BEGIN = "<!-- wos:context:begin -->"
MARKER_END = "<!-- wos:context:end -->"


class AgentsMd(BaseModel):
    """The AGENTS.md file with context manifest between markers.

    Entity (not frozen) -- content changes via update_manifest().
    """

    path: str
    content: str

    # -- String representations -----------------------------------------------

    def __str__(self) -> str:
        lines = self.content.count("\n")
        return f"AgentsMd({self.path}, {lines} lines)"

    def __repr__(self) -> str:
        return f"AgentsMd(path={self.path!r}, content_length={len(self.content)})"

    # -- Construction ---------------------------------------------------------

    @classmethod
    def from_content(cls, path: str, content: str) -> AgentsMd:
        """Parse existing AGENTS.md content."""
        return cls(path=path, content=content)

    @classmethod
    def from_template(cls, path: str) -> AgentsMd:
        """Create new AGENTS.md from template."""
        content = (
            "# AGENTS.md\n"
            "\n"
            "## Context\n"
            "\n"
            f"{MARKER_BEGIN}\n"
            f"{MARKER_END}\n"
        )
        return cls(path=path, content=content)

    @classmethod
    def from_json(cls, data: dict) -> AgentsMd:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls(**data)

    # -- Representations ------------------------------------------------------

    def to_markdown(self) -> str:
        """Return full file content as markdown."""
        return self.content

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return {"path": self.path, "content": self.content}

    # -- Manifest update ------------------------------------------------------

    def update_manifest(self, areas: list) -> AgentsMd:
        """Re-render the manifest between markers and return a new AgentsMd.

        Takes a list of ContextArea objects, generates manifest table,
        and replaces content between markers.  Returns a new instance;
        does not mutate self.
        """
        manifest = self._render_manifest(areas)
        updated_content = self._replace_between_markers(self.content, manifest)
        return AgentsMd(path=self.path, content=updated_content)

    @staticmethod
    def _render_manifest(areas: list) -> str:
        """Generate manifest table from ContextArea list.

        Each area contributes a single row via area.to_manifest_entry().
        Returns the content to place between markers (not including markers).
        """
        if not areas:
            return ""
        parts: List[str] = [
            "| Area | Description |",
            "|------|-------------|",
        ]
        for area in areas:
            parts.append(area.to_manifest_entry())
        return "\n".join(parts)

    @staticmethod
    def _replace_between_markers(content: str, manifest: str) -> str:
        """Replace content between markers, or add markers if missing."""
        begin_idx = content.find(MARKER_BEGIN)
        end_idx = content.find(MARKER_END)

        if begin_idx != -1 and end_idx != -1:
            before = content[:begin_idx + len(MARKER_BEGIN)]
            after = content[end_idx:]
            if manifest:
                return f"{before}\n{manifest}\n{after}"
            return f"{before}\n{after}"

        # No markers found -- append ## Context section
        section = (
            "\n## Context\n"
            "\n"
            f"{MARKER_BEGIN}\n"
        )
        if manifest:
            section += f"{manifest}\n"
        section += f"{MARKER_END}\n"

        return content.rstrip("\n") + "\n" + section

    # -- Validation -----------------------------------------------------------

    def validate_self(self, deep: bool = False) -> List[ValidationIssue]:
        """Check that markers exist and content is non-empty.

        Returns list[ValidationIssue] -- empty when valid.
        """
        issues: List[ValidationIssue] = []

        if not self.content.strip():
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="AGENTS.md is empty",
                    severity=IssueSeverity.WARN,
                    validator="AgentsMd.validate_self",
                    suggestion="Generate AGENTS.md via discovery",
                )
            )
            return issues

        if MARKER_BEGIN not in self.content or MARKER_END not in self.content:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="AGENTS.md is missing WOS context markers",
                    severity=IssueSeverity.WARN,
                    validator="AgentsMd.validate_self",
                    suggestion="Run discovery to add context markers",
                )
            )

        return issues

    @property
    def is_valid(self) -> bool:
        """True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0
