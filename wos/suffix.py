"""Typed file suffix utilities.

Extracts document type from compound markdown suffixes like
``foo.research.md`` → ``"research"``.

Known type suffixes: research, plan, design, context, prompt.
Files without a type suffix (plain ``.md``) return None.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Recognized document-type suffixes (the part before .md)
KNOWN_TYPE_SUFFIXES = frozenset({
    "research",
    "plan",
    "design",
    "context",
    "prompt",
})


def type_from_path(path: Path) -> Optional[str]:
    """Extract document type from a compound suffix.

    Examples:
        >>> type_from_path(Path("api-latency.research.md"))
        'research'
        >>> type_from_path(Path("2026-03-13-cross-platform.plan.md"))
        'plan'
        >>> type_from_path(Path("plain-document.md"))
        >>> type_from_path(Path("notes.txt"))

    Args:
        path: File path (only the name is inspected).

    Returns:
        The type string if a known type suffix is present, else None.
    """
    suffixes = path.suffixes  # e.g. ['.research', '.md'] or ['.md']
    if len(suffixes) >= 2 and suffixes[-1] == ".md":
        candidate = suffixes[-2].lstrip(".")  # '.research' → 'research'
        if candidate in KNOWN_TYPE_SUFFIXES:
            return candidate
    return None
