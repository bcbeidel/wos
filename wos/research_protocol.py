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


def format_protocol(protocol: SearchProtocol) -> str:
    """Render search protocol as markdown table for insertion into research document."""
    if not protocol.entries:
        return "No searches recorded.\n"

    lines = []
    lines.append("| Query | Source | Date Range | Found | Used |")
    lines.append("|-------|--------|------------|-------|------|")
    for entry in protocol.entries:
        date_range = entry.date_range if entry.date_range else "\u2014"
        lines.append(
            f"| {entry.query} | {entry.source} | {date_range} "
            f"| {entry.results_found} | {entry.results_used} |"
        )

    if protocol.not_searched:
        lines.append("")
        lines.append(
            f"**Not searched:** {', '.join(protocol.not_searched)}"
        )

    lines.append("")
    return "\n".join(lines) + "\n"
