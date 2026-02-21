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

_SEVERITY_LABELS: Dict[str, str] = {
    "fail": "Failures",
    "warn": "Warnings",
    "info": "Info",
}


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


def format_summary(report: dict, *, color: bool = False) -> str:
    """Render a compact one-line-per-issue health report."""
    status = report["status"]
    files_checked = report["files_checked"]
    issues = report.get("issues", [])
    budget = report.get("token_budget", {})

    parts: List[str] = []

    # Status line
    parts.append(
        _status_line(status, len(issues), files_checked, color=color)
    )

    # Issue lines
    if issues:
        parts.append("")  # blank line
        sorted_issues = sorted(
            issues,
            key=lambda i: (
                _SEVERITY_ORDER.get(i["severity"], 99),
                i["file"],
            ),
        )
        for issue in sorted_issues:
            sev = issue["severity"]
            label = _colorize(sev.upper().ljust(4), sev, color=color)
            parts.append(f"  {label}  {issue['file']}  {issue['issue']}")

    # Token budget
    if budget:
        parts.append("")
        parts.append(_format_token_budget(budget, detailed=False, color=color))

    return "\n".join(parts) + "\n"


def format_detailed(report: dict, *, color: bool = False) -> str:
    """Render a severity-grouped health report with suggestions."""
    status = report["status"]
    files_checked = report["files_checked"]
    issues = report.get("issues", [])
    budget = report.get("token_budget", {})

    parts: List[str] = []

    # Status line
    parts.append(
        _status_line(status, len(issues), files_checked, color=color)
    )

    # Group issues by severity
    for sev in ("fail", "warn", "info"):
        sev_issues = sorted(
            [i for i in issues if i["severity"] == sev],
            key=lambda i: i["file"],
        )
        if not sev_issues:
            continue

        label = _SEVERITY_LABELS[sev]
        count = len(sev_issues)
        header = _colorize(f"{label} ({count})", sev, color=color)
        parts.append("")
        parts.append(header)

        # Group by file within severity
        current_file: Optional[str] = None
        for issue in sev_issues:
            if issue["file"] != current_file:
                current_file = issue["file"]
                parts.append(f"  {current_file}")
            parts.append(f"    {issue['issue']}")
            if issue.get("suggestion"):
                parts.append(f"    → {issue['suggestion']}")

    # Token budget (detailed with areas)
    if budget:
        parts.append("")
        parts.append(
            _format_token_budget(budget, detailed=True, color=color)
        )

    return "\n".join(parts) + "\n"
