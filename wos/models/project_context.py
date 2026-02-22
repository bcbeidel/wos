"""ProjectContext — aggregate root for the project's context graph.

Owns the top-level project state: areas, AGENTS.md, CLAUDE.md, and
the rules file.  Delegates validation to each owned object.

This is the aggregate root in DDD terms — all project-wide queries
and mutations should go through this object.
"""
from __future__ import annotations

from typing import Iterator, List, Optional

from pydantic import BaseModel

from wos.models.agents_md import AgentsMd
from wos.models.claude_md import ClaudeMd
from wos.models.context_area import ContextArea
from wos.models.rules_file import RulesFile
from wos.models.core import ValidationIssue


class ProjectContext(BaseModel):
    """Aggregate root for a project's structured context.

    Entity (not frozen) — areas and owned files can be mutated.
    """

    root: str
    areas: List[ContextArea] = []
    agents_md: Optional[AgentsMd] = None
    claude_md: Optional[ClaudeMd] = None
    rules_file: Optional[RulesFile] = None

    # ── String representations ────────────────────────────────────

    def __str__(self) -> str:
        n = len(self.areas)
        label = "area" if n == 1 else "areas"
        return f"ProjectContext({self.root}, {n} {label})"

    def __repr__(self) -> str:
        return (
            f"ProjectContext(root={self.root!r}, "
            f"areas={len(self.areas)}, "
            f"agents_md={'yes' if self.agents_md else 'no'}, "
            f"claude_md={'yes' if self.claude_md else 'no'}, "
            f"rules_file={'yes' if self.rules_file else 'no'})"
        )

    # ── Collection protocol (over areas) ──────────────────────────

    def __len__(self) -> int:
        return len(self.areas)

    def __iter__(self) -> Iterator[ContextArea]:
        return iter(self.areas)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return any(a.name == item for a in self.areas)
        return item in self.areas

    # ── Validation protocol ───────────────────────────────────────

    def validate_self(self, deep: bool = False) -> List[ValidationIssue]:
        """Validate by delegating to all owned objects.

        Collects issues from each area, agents_md, claude_md, and
        rules_file.  Returns the full aggregated list.

        Parameters
        ----------
        deep : bool
            When True, enables I/O-bound checks (e.g., URL reachability).
        """
        issues: List[ValidationIssue] = []

        # Delegate to each area
        for area in self.areas:
            issues.extend(area.validate_self(deep=deep))

        # Delegate to owned file entities
        if self.agents_md is not None:
            issues.extend(self.agents_md.validate_self(deep=deep))

        if self.claude_md is not None:
            issues.extend(self.claude_md.validate_self(deep=deep))

        if self.rules_file is not None:
            issues.extend(self.rules_file.validate_self(deep=deep))

        return issues

    @property
    def is_valid(self) -> bool:
        """True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0

    # ── Serialization protocol ────────────────────────────────────

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return {
            "root": self.root,
            "areas": [a.model_dump(mode="json") for a in self.areas],
            "agents_md": self.agents_md.to_json() if self.agents_md else None,
            "claude_md": self.claude_md.to_json() if self.claude_md else None,
            "rules_file": self.rules_file.to_json() if self.rules_file else None,
        }

    @classmethod
    def from_json(cls, data: dict) -> ProjectContext:
        """Construct from a plain dict (e.g. parsed JSON)."""
        areas = [ContextArea(**a) for a in data.get("areas", [])]

        agents_md = None
        if data.get("agents_md") is not None:
            agents_md = AgentsMd.from_json(data["agents_md"])

        claude_md = None
        if data.get("claude_md") is not None:
            claude_md = ClaudeMd.from_json(data["claude_md"])

        rules_file = None
        if data.get("rules_file") is not None:
            rules_file = RulesFile.from_json(data["rules_file"])

        return cls(
            root=data["root"],
            areas=areas,
            agents_md=agents_md,
            claude_md=claude_md,
            rules_file=rules_file,
        )

    # ── Token estimation ──────────────────────────────────────────

    def get_estimated_tokens(self) -> int:
        """Sum of estimated tokens across all areas."""
        return sum(a.get_estimated_tokens() for a in self.areas)
