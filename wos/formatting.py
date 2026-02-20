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
