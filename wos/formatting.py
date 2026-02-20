"""Human-readable health report formatting.

Pure functions that take a health report dict and return formatted strings.
The report dict has keys: status, files_checked, issues, triggers, token_budget.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ── ANSI color codes ────────────────────────────────────────────

_COLORS: Dict[str, str] = {
    "fail": "\033[31m",   # red
    "warn": "\033[33m",   # yellow
    "info": "\033[2m",    # dim
    "pass": "\033[32m",   # green
}
_RESET = "\033[0m"

_SEVERITY_ORDER: Dict[str, int] = {"fail": 0, "warn": 1, "info": 2}


def _colorize(text: str, severity: str, *, color: bool) -> str:
    """Wrap text in ANSI color codes for the given severity."""
    if not color:
        return text
    code = _COLORS.get(severity, "")
    if not code:
        return text
    return f"{code}{text}{_RESET}"


def _status_line(
    status: str, issue_count: int, file_count: int, *, color: bool
) -> str:
    """Render the top-level status line."""
    label = status.upper()
    issues_word = "issue" if issue_count == 1 else "issues"
    files_word = "file" if file_count == 1 else "files"
    status_colored = _colorize(label, status, color=color)
    return (
        f"Health: {status_colored} "
        f"({issue_count} {issues_word} in {file_count} {files_word})"
    )


def _format_token_budget(
    budget: dict, *, detailed: bool, color: bool
) -> str:
    """Render token budget as a summary line or detailed breakdown."""
    total = budget["total_estimated_tokens"]
    threshold = budget["warning_threshold"]
    over = budget.get("over_budget", False)
    areas = budget.get("areas", [])

    headline = f"Token budget: {total:,} / {threshold:,}"
    if over and color:
        headline = _colorize(headline, "warn", color=True)

    if not detailed or not areas:
        return headline

    # Detailed: add area count and per-area lines
    headline += f" ({len(areas)} {'area' if len(areas) == 1 else 'areas'})"
    lines = [headline]

    # Find max area name length for alignment
    max_name = max(len(a["area"]) for a in areas) if areas else 0
    for area in areas:
        name = area["area"].ljust(max_name)
        tokens = f"{area['estimated_tokens']:,}"
        files = area["files"]
        files_word = "file" if files == 1 else "files"
        lines.append(f"  {name}  {tokens:>8} ({files} {files_word})")

    return "\n".join(lines)
