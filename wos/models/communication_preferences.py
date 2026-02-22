"""CommunicationPreferences -- value object for communication dimensions."""
from __future__ import annotations

from typing import Dict, List, Tuple

from pydantic import BaseModel, ConfigDict

from wos.models.core import IssueSeverity, ValidationIssue

# Valid dimensions and their levels
DIMENSIONS: Dict[str, List[str]] = {
    "directness": ["blunt", "balanced", "diplomatic"],
    "verbosity": ["terse", "moderate", "thorough"],
    "depth": ["just-answers", "context-when-useful", "teach-me"],
    "expertise": ["beginner", "intermediate", "expert"],
    "tone": ["casual", "neutral", "formal"],
}

# Instruction text for each (dimension, level) pair
DIMENSION_INSTRUCTIONS: Dict[Tuple[str, str], str] = {
    ("directness", "blunt"): (
        "Be direct. State problems and disagreements plainly "
        "without hedging or softening."
    ),
    ("directness", "balanced"): (
        "Be straightforward but considerate. State issues clearly "
        "while acknowledging tradeoffs."
    ),
    ("directness", "diplomatic"): (
        "Frame feedback constructively. Lead with positives, "
        "suggest improvements gently."
    ),
    ("verbosity", "terse"): (
        "Keep responses concise. Skip preamble and unnecessary elaboration."
    ),
    ("verbosity", "moderate"): (
        "Provide enough detail to be clear without being exhaustive."
    ),
    ("verbosity", "thorough"): (
        "Be comprehensive. Include context, examples, and edge cases."
    ),
    ("depth", "just-answers"): (
        "Give the answer directly. Skip explanations unless asked."
    ),
    ("depth", "context-when-useful"): (
        "Provide context when it aids understanding, but don't over-explain."
    ),
    ("depth", "teach-me"): (
        "Explain the reasoning and principles behind recommendations. "
        "Help me learn, not just execute."
    ),
    ("expertise", "beginner"): (
        "Assume limited domain knowledge. Define terms and explain concepts."
    ),
    ("expertise", "intermediate"): (
        "Assume working knowledge. Skip basics but explain advanced concepts."
    ),
    ("expertise", "expert"): (
        "Assume expert-level knowledge. Skip fundamentals."
    ),
    ("tone", "casual"): (
        "Keep it casual and conversational. Informal language is fine."
    ),
    ("tone", "neutral"): (
        "Neutral and professional. No sycophancy or forced enthusiasm."
    ),
    ("tone", "formal"): (
        "Maintain a formal, professional tone throughout."
    ),
}

_DISPLAY_NAMES: Dict[str, str] = {
    "directness": "Directness",
    "verbosity": "Verbosity",
    "depth": "Depth",
    "expertise": "Expertise",
    "tone": "Tone",
}


class CommunicationPreferences(BaseModel):
    """Communication style preferences as structured dimensions.

    Frozen value object -- immutable after construction.
    Each dimension maps to a level that controls a specific aspect
    of communication style (directness, verbosity, depth, expertise, tone).
    """

    model_config = ConfigDict(frozen=True)

    dimensions: Dict[str, str]  # e.g. {"directness": "blunt", "tone": "casual"}

    # -- String representations ----------------------------------------

    def __str__(self) -> str:
        count = len(self.dimensions)
        return f"CommunicationPreferences({count} dimensions)"

    def __repr__(self) -> str:
        return f"CommunicationPreferences(dimensions={self.dimensions!r})"

    # -- Render protocol -----------------------------------------------

    def render_section(self) -> str:
        """Render as markdown instruction lines.

        Each dimension produces a bullet with bold label and instruction text.
        Dimensions with unrecognized (dim, level) pairs are silently skipped.
        """
        lines: List[str] = []
        for dim, level in self.dimensions.items():
            if (dim, level) in DIMENSION_INSTRUCTIONS:
                display = _DISPLAY_NAMES.get(dim, dim.title())
                instruction = DIMENSION_INSTRUCTIONS[(dim, level)]
                lines.append(f"- **{display}:** {instruction}")
        return "\n".join(lines)

    # -- JSON protocol -------------------------------------------------

    def to_json(self) -> dict:
        """Serialize to a plain dict suitable for JSON."""
        return {"dimensions": dict(self.dimensions)}

    @classmethod
    def from_json(cls, data: dict) -> CommunicationPreferences:
        """Construct from a plain dict (e.g. parsed JSON)."""
        return cls(**data)

    # -- Validation protocol -------------------------------------------

    def validate_self(self, deep: bool = False) -> List[ValidationIssue]:
        """Check that all dimension keys and levels are recognized.

        Returns list[ValidationIssue] -- empty when fully valid.
        """
        issues: List[ValidationIssue] = []
        for dim, level in self.dimensions.items():
            if dim not in DIMENSIONS:
                issues.append(
                    ValidationIssue(
                        file="preferences",
                        issue=f"Unknown dimension: {dim}",
                        severity=IssueSeverity.WARN,
                        validator="CommunicationPreferences.validate_self",
                        suggestion=f"Valid dimensions: {', '.join(DIMENSIONS.keys())}",
                    )
                )
            elif level not in DIMENSIONS[dim]:
                issues.append(
                    ValidationIssue(
                        file="preferences",
                        issue=f"Unknown level '{level}' for dimension '{dim}'",
                        severity=IssueSeverity.WARN,
                        validator="CommunicationPreferences.validate_self",
                        suggestion=f"Valid levels: {', '.join(DIMENSIONS[dim])}",
                    )
                )
        return issues

    @property
    def is_valid(self) -> bool:
        """Shortcut: True when validate_self() returns no issues."""
        return len(self.validate_self()) == 0
