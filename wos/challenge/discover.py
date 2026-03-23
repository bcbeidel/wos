"""Assumption-to-document matching for the /wos:challenge skill."""

from __future__ import annotations

from typing import Callable


def keyword_score(assumption: str, text: str) -> float:
    """Score relevance of text to an assumption via keyword overlap.

    Tokenizes both strings, filters tokens under 3 characters, and
    returns the fraction of assumption tokens found in text. Returns 0.0
    if the assumption has no usable tokens.

    This is the default scorer. The interface (assumption, text) -> float
    is swappable for more sophisticated matching later.

    Args:
        assumption: The assumption claim text.
        text: The document text to match against (typically name + description).

    Returns:
        Float between 0.0 and 1.0 inclusive.
    """
    assumption_tokens = [
        t for t in assumption.lower().split() if len(t) >= 3
    ]
    if not assumption_tokens:
        return 0.0
    text_lower = text.lower()
    matched = sum(1 for t in assumption_tokens if t in text_lower)
    return matched / len(assumption_tokens)
