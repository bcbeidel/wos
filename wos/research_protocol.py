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


def format_protocol_summary(protocol: SearchProtocol) -> str:
    """One-line summary of search protocol."""
    n_searches = len(protocol.entries)
    sources = {e.source for e in protocol.entries}
    n_sources = len(sources)
    total_found = sum(e.results_found for e in protocol.entries)
    total_used = sum(e.results_used for e in protocol.entries)

    if n_searches == 0:
        return "0 searches, 0 results found, 0 used"

    search_word = "search" if n_searches == 1 else "searches"
    source_word = "source" if n_sources == 1 else "sources"

    return (
        f"{n_searches} {search_word} across {n_sources} {source_word}, "
        f"{total_found} results found, {total_used} used"
    )
