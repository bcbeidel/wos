"""Search protocol logging for research auditability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchEntry:
    """A single search performed during research."""

    query: str
    source: str
    date_range: Optional[str]
    results_found: int
    results_used: int


@dataclass
class SearchProtocol:
    """Complete search protocol for a research session."""

    entries: List[SearchEntry] = field(default_factory=list)
    not_searched: List[str] = field(default_factory=list)
