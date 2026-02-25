"""Communication preferences — dimension mapping and CLAUDE.md writer.

Captures user communication preferences as structured dimensions and
writes them as LLM instructions in CLAUDE.md using marker-based sections.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# ── Markers ──────────────────────────────────────────────────────

COMM_MARKER_BEGIN = "<!-- wos:communication:begin -->"
COMM_MARKER_END = "<!-- wos:communication:end -->"

# ── Dimensions ───────────────────────────────────────────────────

DIMENSIONS: Dict[str, List[str]] = {
    "directness": ["blunt", "balanced", "diplomatic"],
    "verbosity": ["terse", "moderate", "thorough"],
    "depth": ["just-answers", "context-when-useful", "teach-me"],
    "expertise": ["beginner", "intermediate", "expert"],
    "tone": ["casual", "neutral", "formal"],
}

DIMENSION_INSTRUCTIONS: Dict[tuple, str] = {
    # Directness
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
    # Verbosity
    ("verbosity", "terse"): (
        "Keep responses concise. Skip preamble and unnecessary elaboration."
    ),
    ("verbosity", "moderate"): (
        "Provide enough detail to be clear without being exhaustive."
    ),
    ("verbosity", "thorough"): (
        "Be comprehensive. Include context, examples, and edge cases."
    ),
    # Depth
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
    # Expertise
    ("expertise", "beginner"): (
        "Assume limited domain knowledge. Define terms and explain concepts."
    ),
    ("expertise", "intermediate"): (
        "Assume working knowledge. Skip basics but explain advanced concepts."
    ),
    ("expertise", "expert"): (
        "Assume expert-level knowledge. Skip fundamentals."
    ),
    # Tone
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

# Display names for dimensions
_DISPLAY_NAMES = {
    "directness": "Directness",
    "verbosity": "Verbosity",
    "depth": "Depth",
    "expertise": "Expertise",
    "tone": "Tone",
}


# ── Render ───────────────────────────────────────────────────────


def render_preferences(prefs: Dict[str, str]) -> str:
    """Render preference dimensions as markdown instruction lines.

    Args:
        prefs: Mapping of dimension name to level (e.g., {"directness": "blunt"}).

    Returns:
        Markdown string with one instruction per dimension.

    Raises:
        ValueError: If an unknown dimension or level is provided.
    """
    lines: List[str] = []
    for dim, level in prefs.items():
        if dim not in DIMENSIONS:
            raise ValueError(f"Unknown dimension: {dim}")
        if level not in DIMENSIONS[dim]:
            raise ValueError(
                f"Unknown level '{level}' for dimension '{dim}'. "
                f"Valid levels: {DIMENSIONS[dim]}"
            )
        instruction = DIMENSION_INSTRUCTIONS[(dim, level)]
        display = _DISPLAY_NAMES[dim]
        lines.append(f"- **{display}:** {instruction}")
    return "\n".join(lines)


# ── Writer ───────────────────────────────────────────────────────


def update_preferences(file_path: str, prefs: Dict[str, str]) -> None:
    """Write communication preferences to CLAUDE.md using markers.

    Creates the file if it doesn't exist. Replaces existing preferences
    section if markers are found. Appends if no markers exist.
    """
    path = Path(file_path)
    rendered = render_preferences(prefs)

    section = (
        f"{COMM_MARKER_BEGIN}\n"
        f"## Communication\n"
        f"\n"
        f"{rendered}\n"
        f"\n"
        f"{COMM_MARKER_END}\n"
    )

    from wos.markers import replace_marker_section

    if not path.exists():
        path.write_text(section, encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    updated = replace_marker_section(
        content, COMM_MARKER_BEGIN, COMM_MARKER_END, section
    )
    path.write_text(updated, encoding="utf-8")
