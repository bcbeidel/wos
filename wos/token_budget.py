"""Token budget estimation for context files.

Estimates the aggregate token cost of context documents using a
word-count heuristic (words * 1.3). No tokenizer dependency.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List

from wos.document_types import Document

_TOKEN_MULTIPLIER = 1.3
_DEFAULT_WARNING_THRESHOLD = 40_000


def estimate_token_budget(
    documents: List[Document],
    warning_threshold: int = _DEFAULT_WARNING_THRESHOLD,
) -> Dict[str, Any]:
    """Estimate token budget for a set of context documents.

    Args:
        documents: Parsed Document objects (caller should filter to context/ only).
        warning_threshold: Token count above which over_budget is True.

    Returns:
        Dict with total_estimated_tokens, warning_threshold, over_budget,
        areas list, and optionally an issue dict if over budget.
    """
    area_totals: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"files": 0, "estimated_tokens": 0}
    )

    for doc in documents:
        area = _extract_area(doc.path)
        word_count = len(doc.raw_content.split())
        tokens = round(word_count * _TOKEN_MULTIPLIER)
        area_totals[area]["files"] += 1
        area_totals[area]["estimated_tokens"] += tokens

    total_tokens = sum(a["estimated_tokens"] for a in area_totals.values())
    over_budget = total_tokens > warning_threshold

    areas = sorted(
        [{"area": name, **data} for name, data in area_totals.items()],
        key=lambda a: a["area"],
    )

    result: Dict[str, Any] = {
        "total_estimated_tokens": total_tokens,
        "warning_threshold": warning_threshold,
        "over_budget": over_budget,
        "areas": areas,
    }

    if over_budget:
        result["issue"] = {
            "file": "context/",
            "issue": (
                f"Total context estimated at ~{total_tokens:,} tokens "
                f"(threshold: {warning_threshold:,}). "
                "Consider reducing content or splitting areas."
            ),
            "severity": "warn",
            "validator": "token_budget",
            "section": None,
            "suggestion": (
                "Review per-area estimated token counts to identify"
                " optimization targets."
            ),
        }

    return result


def _extract_area(path: str) -> str:
    """Extract area name from a context path like 'context/{area}/file.md'."""
    match = re.match(r"context/([^/]+)/", path)
    return match.group(1) if match else "unknown"
