"""ClaudeMd -- entity for the CLAUDE.md file.

Owns the CLAUDE.md content.  Ports logic from discovery.py:
update_claude_md(), _strip_marker_section(), _claude_md_template().

The CLAUDE.md file is a thin pointer -- it contains an @AGENTS.md
reference so Claude Code loads the agents file.  May contain old WOS
context markers (from pre-0.1.9) that need to be stripped.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel

from wos.models.enums import IssueSeverity
from wos.models.validation_issue import ValidationIssue

AGENTS_REF = "@AGENTS.md"
MARKER_BEGIN = "<!-- wos:context:begin -->"
MARKER_END = "<!-- wos:context:end -->"


class ClaudeMd(BaseModel):
    """The CLAUDE.md file -- thin pointer to AGENTS.md.

    Entity (not frozen) -- content changes via ensure_agents_ref()
    and strip_old_markers().
    """

    path: str
    content: str

    # -- String representations -----------------------------------------------

    def __str__(self) -> str:
        lines = self.content.count("\n")
        return f"ClaudeMd({self.path}, {lines} lines)"

    def __repr__(self) -> str:
        return f"ClaudeMd(path={self.path!r}, content_length={len(self.content)})"

    # -- Construction ---------------------------------------------------------

    @classmethod
    def from_content(cls, path: str, content: str) -> ClaudeMd:
        """Parse existing CLAUDE.md content."""
        return cls(path=path, content=content)

    @classmethod
    def from_template(cls, path: str) -> ClaudeMd:
        """Create new CLAUDE.md as a thin pointer to AGENTS.md."""
        return cls(path=path, content=f"{AGENTS_REF}\n")

    @classmethod
    def from_json(cls, data: dict) -> ClaudeMd:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls(**data)

    # -- Representations ------------------------------------------------------

    def to_markdown(self) -> str:
        """Return full file content as markdown."""
        return self.content

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return {"path": self.path, "content": self.content}

    # -- Mutations (return new instance) --------------------------------------

    def ensure_agents_ref(self) -> ClaudeMd:
        """Add @AGENTS.md reference if not present.  Returns new ClaudeMd.

        If the reference already exists, returns a copy with identical content.
        """
        if AGENTS_REF in self.content:
            return ClaudeMd(path=self.path, content=self.content)
        new_content = self.content.rstrip("\n") + "\n\n" + AGENTS_REF + "\n"
        return ClaudeMd(path=self.path, content=new_content)

    def strip_old_markers(self) -> ClaudeMd:
        """Remove old WOS context markers and content between them.

        Also removes a preceding ``## Context`` heading if present.
        Returns a new ClaudeMd; does not mutate self.

        Ported from discovery._strip_marker_section().
        """
        if MARKER_BEGIN not in self.content or MARKER_END not in self.content:
            return ClaudeMd(path=self.path, content=self.content)

        begin_idx = self.content.find(MARKER_BEGIN)
        end_idx = self.content.find(MARKER_END)
        end_idx += len(MARKER_END)

        before = self.content[:begin_idx]
        after = self.content[end_idx:]

        # Try to also remove preceding ## Context heading
        stripped_before = before.rstrip()
        if stripped_before.endswith("## Context"):
            before = stripped_before[:-len("## Context")]

        # Clean up whitespace
        result = before.rstrip("\n") + "\n"
        after_stripped = after.lstrip("\n")
        if after_stripped:
            result += "\n" + after_stripped

        return ClaudeMd(path=self.path, content=result)

    # -- Validation -----------------------------------------------------------

    def validate_self(self, deep: bool = False) -> List[ValidationIssue]:
        """Check that @AGENTS.md reference exists.

        Returns list[ValidationIssue] -- empty when valid.
        """
        issues: List[ValidationIssue] = []

        if not self.content.strip():
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="CLAUDE.md is empty",
                    severity=IssueSeverity.WARN,
                    validator="ClaudeMd.validate_self",
                    suggestion="Add @AGENTS.md reference",
                )
            )
            return issues

        if AGENTS_REF not in self.content:
            issues.append(
                ValidationIssue(
                    file=self.path,
                    issue="CLAUDE.md is missing @AGENTS.md reference",
                    severity=IssueSeverity.WARN,
                    validator="ClaudeMd.validate_self",
                    suggestion="Add @AGENTS.md to CLAUDE.md",
                )
            )

        return issues

    @property
    def is_valid(self) -> bool:
        """True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0
