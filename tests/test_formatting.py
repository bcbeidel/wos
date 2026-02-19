"""Tests for wos.formatting — human-readable health report formatting."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from wos.formatting import (
    _COLORS,
    _RESET,
    _SEVERITY_ORDER,
    _colorize,
    _format_token_budget,
    _status_line,
    format_detailed,
    format_summary,
)


# ── helpers ─────────────────────────────────────────────────────


def _make_report(
    *,
    status: str = "pass",
    files_checked: int = 5,
    issues: Optional[List[Dict[str, Any]]] = None,
    triggers: Optional[List[Dict[str, Any]]] = None,
    token_budget: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a minimal health report dict for testing."""
    report: Dict[str, Any] = {
        "status": status,
        "files_checked": files_checked,
    }
    if issues is not None:
        report["issues"] = issues
    if triggers is not None:
        report["triggers"] = triggers
    if token_budget is not None:
        report["token_budget"] = token_budget
    return report


def _make_issue(
    *,
    file: str = "context/area/topic.md",
    issue: str = "Something is wrong",
    severity: str = "warn",
    validator: str = "test_validator",
    section: Optional[str] = None,
    suggestion: Optional[str] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "file": file,
        "issue": issue,
        "severity": severity,
        "validator": validator,
    }
    if section is not None:
        result["section"] = section
    if suggestion is not None:
        result["suggestion"] = suggestion
    return result


def _make_budget(
    *,
    total_estimated_tokens: int = 5000,
    warning_threshold: int = 10000,
    over_budget: bool = False,
    areas: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    budget: Dict[str, Any] = {
        "total_estimated_tokens": total_estimated_tokens,
        "warning_threshold": warning_threshold,
        "over_budget": over_budget,
    }
    if areas is not None:
        budget["areas"] = areas
    return budget


# ── TestColorize ────────────────────────────────────────────────


class TestColorize:
    """Tests for _colorize()."""

    def test_no_color_returns_plain(self) -> None:
        assert _colorize("hello", "fail", color=False) == "hello"

    def test_color_wraps_with_ansi(self) -> None:
        result = _colorize("hello", "fail", color=True)
        assert result == f"\033[31mhello{_RESET}"

    def test_correct_code_for_fail(self) -> None:
        result = _colorize("x", "fail", color=True)
        assert result.startswith("\033[31m")
        assert result.endswith(_RESET)

    def test_correct_code_for_warn(self) -> None:
        result = _colorize("x", "warn", color=True)
        assert result.startswith("\033[33m")
        assert result.endswith(_RESET)

    def test_correct_code_for_info(self) -> None:
        result = _colorize("x", "info", color=True)
        assert result.startswith("\033[2m")
        assert result.endswith(_RESET)

    def test_correct_code_for_pass(self) -> None:
        result = _colorize("x", "pass", color=True)
        assert result.startswith("\033[32m")
        assert result.endswith(_RESET)

    def test_unknown_severity_returns_plain(self) -> None:
        result = _colorize("x", "unknown", color=True)
        assert result == "x"


# ── TestSeverityOrder ───────────────────────────────────────────


class TestSeverityOrder:
    """Tests for _SEVERITY_ORDER sort ordering."""

    def test_fail_less_than_warn(self) -> None:
        assert _SEVERITY_ORDER["fail"] < _SEVERITY_ORDER["warn"]

    def test_warn_less_than_info(self) -> None:
        assert _SEVERITY_ORDER["warn"] < _SEVERITY_ORDER["info"]

    def test_fail_less_than_info(self) -> None:
        assert _SEVERITY_ORDER["fail"] < _SEVERITY_ORDER["info"]


# ── TestStatusLine ──────────────────────────────────────────────


class TestStatusLine:
    """Tests for _status_line()."""

    def test_pass_status(self) -> None:
        line = _status_line("pass", 0, 5, color=False)
        assert line == "Health: PASS (0 issues in 5 files)"

    def test_fail_status(self) -> None:
        line = _status_line("fail", 3, 10, color=False)
        assert line == "Health: FAIL (3 issues in 10 files)"

    def test_warn_status(self) -> None:
        line = _status_line("warn", 2, 4, color=False)
        assert line == "Health: WARN (2 issues in 4 files)"

    def test_singular_issue(self) -> None:
        line = _status_line("fail", 1, 5, color=False)
        assert "1 issue in" in line
        assert "issues" not in line

    def test_singular_file(self) -> None:
        line = _status_line("pass", 0, 1, color=False)
        assert "1 file)" in line
        assert "files" not in line

    def test_plural_issues_and_files(self) -> None:
        line = _status_line("fail", 3, 10, color=False)
        assert "3 issues" in line
        assert "10 files" in line

    def test_color_wraps_status(self) -> None:
        line = _status_line("fail", 1, 1, color=True)
        assert "\033[31m" in line
        assert _RESET in line
        assert "FAIL" in line


# ── TestFormatTokenBudget ───────────────────────────────────────


class TestFormatTokenBudget:
    """Tests for _format_token_budget()."""

    def test_summary_one_liner(self) -> None:
        budget = _make_budget(total_estimated_tokens=5000, warning_threshold=10000)
        result = _format_token_budget(budget, detailed=False, color=False)
        assert result == "Token budget: 5,000 / 10,000"

    def test_detailed_with_areas(self) -> None:
        budget = _make_budget(
            total_estimated_tokens=3000,
            warning_threshold=10000,
            areas=[
                {"area": "python", "estimated_tokens": 2000, "files": 3},
                {"area": "testing", "estimated_tokens": 1000, "files": 1},
            ],
        )
        result = _format_token_budget(budget, detailed=True, color=False)
        lines = result.split("\n")
        assert "Token budget: 3,000 / 10,000 (2 areas)" in lines[0]
        assert "python" in lines[1]
        assert "2,000" in lines[1]
        assert "3 files" in lines[1]
        assert "testing" in lines[2]
        assert "1,000" in lines[2]
        assert "1 file)" in lines[2]

    def test_detailed_without_areas_falls_back_to_summary(self) -> None:
        budget = _make_budget(total_estimated_tokens=5000, warning_threshold=10000)
        result = _format_token_budget(budget, detailed=True, color=False)
        assert result == "Token budget: 5,000 / 10,000"

    def test_over_budget_colored(self) -> None:
        budget = _make_budget(
            total_estimated_tokens=15000,
            warning_threshold=10000,
            over_budget=True,
        )
        result = _format_token_budget(budget, detailed=False, color=True)
        assert "\033[33m" in result  # warn color (yellow)
        assert _RESET in result

    def test_over_budget_no_color(self) -> None:
        budget = _make_budget(
            total_estimated_tokens=15000,
            warning_threshold=10000,
            over_budget=True,
        )
        result = _format_token_budget(budget, detailed=False, color=False)
        assert "\033[" not in result
        assert "15,000 / 10,000" in result

    def test_single_area_label(self) -> None:
        budget = _make_budget(
            total_estimated_tokens=2000,
            warning_threshold=10000,
            areas=[{"area": "python", "estimated_tokens": 2000, "files": 3}],
        )
        result = _format_token_budget(budget, detailed=True, color=False)
        assert "(1 area)" in result


# ── TestFormatSummary ───────────────────────────────────────────


class TestFormatSummary:
    """Tests for format_summary()."""

    def test_clean_report(self) -> None:
        report = _make_report(status="pass", files_checked=5)
        result = format_summary(report, color=False)
        assert "Health: PASS (0 issues in 5 files)" in result

    def test_issues_sorted_by_severity(self) -> None:
        issues = [
            _make_issue(severity="info", file="a.md", issue="info issue"),
            _make_issue(severity="fail", file="b.md", issue="fail issue"),
            _make_issue(severity="warn", file="c.md", issue="warn issue"),
        ]
        report = _make_report(status="fail", issues=issues)
        result = format_summary(report, color=False)
        lines = [l for l in result.split("\n") if l.strip().startswith(("FAIL", "WARN", "INFO"))]
        assert len(lines) == 3
        assert "FAIL" in lines[0]
        assert "WARN" in lines[1]
        assert "INFO" in lines[2]

    def test_sorted_by_path_within_severity(self) -> None:
        issues = [
            _make_issue(severity="warn", file="z/topic.md", issue="z issue"),
            _make_issue(severity="warn", file="a/topic.md", issue="a issue"),
        ]
        report = _make_report(status="warn", issues=issues)
        result = format_summary(report, color=False)
        lines = [l for l in result.split("\n") if l.strip().startswith("WARN")]
        assert "a/topic.md" in lines[0]
        assert "z/topic.md" in lines[1]

    def test_no_blank_block_when_no_issues(self) -> None:
        report = _make_report(status="pass", files_checked=3)
        result = format_summary(report, color=False)
        # Should not have consecutive blank lines (no empty issues block)
        assert "\n\n\n" not in result

    def test_includes_token_budget(self) -> None:
        budget = _make_budget(total_estimated_tokens=5000, warning_threshold=10000)
        report = _make_report(status="pass", files_checked=3, token_budget=budget)
        result = format_summary(report, color=False)
        assert "Token budget: 5,000 / 10,000" in result

    def test_ends_with_newline(self) -> None:
        report = _make_report(status="pass", files_checked=3)
        result = format_summary(report, color=False)
        assert result.endswith("\n")


# ── TestFormatDetailed ──────────────────────────────────────────


class TestFormatDetailed:
    """Tests for format_detailed()."""

    def test_groups_by_severity(self) -> None:
        issues = [
            _make_issue(severity="fail", file="a.md", issue="fail issue"),
            _make_issue(severity="warn", file="b.md", issue="warn issue"),
            _make_issue(severity="info", file="c.md", issue="info issue"),
        ]
        report = _make_report(status="fail", issues=issues)
        result = format_detailed(report, color=False)
        fail_pos = result.index("Failures (1)")
        warn_pos = result.index("Warnings (1)")
        info_pos = result.index("Info (1)")
        assert fail_pos < warn_pos < info_pos

    def test_suggestion_arrows(self) -> None:
        issues = [
            _make_issue(
                severity="fail",
                file="a.md",
                issue="broken link",
                suggestion="Fix the link",
            ),
        ]
        report = _make_report(status="fail", issues=issues)
        result = format_detailed(report, color=False)
        assert "\u2192 Fix the link" in result

    def test_no_arrow_when_no_suggestion(self) -> None:
        issues = [
            _make_issue(severity="fail", file="a.md", issue="broken link"),
        ]
        report = _make_report(status="fail", issues=issues)
        result = format_detailed(report, color=False)
        assert "\u2192" not in result

    def test_multiple_issues_same_file_grouped(self) -> None:
        issues = [
            _make_issue(severity="fail", file="a.md", issue="issue one"),
            _make_issue(severity="fail", file="a.md", issue="issue two"),
        ]
        report = _make_report(status="fail", issues=issues)
        result = format_detailed(report, color=False)
        # File should appear only once
        assert result.count("  a.md") == 1
        assert "issue one" in result
        assert "issue two" in result

    def test_detailed_token_budget_shows_areas(self) -> None:
        budget = _make_budget(
            total_estimated_tokens=3000,
            warning_threshold=10000,
            areas=[
                {"area": "python", "estimated_tokens": 2000, "files": 3},
                {"area": "testing", "estimated_tokens": 1000, "files": 1},
            ],
        )
        report = _make_report(
            status="pass", files_checked=4, token_budget=budget
        )
        result = format_detailed(report, color=False)
        assert "(2 areas)" in result
        assert "python" in result
        assert "testing" in result

    def test_clean_report(self) -> None:
        report = _make_report(status="pass", files_checked=5)
        result = format_detailed(report, color=False)
        assert "Health: PASS" in result
        # No severity sections for a clean report
        assert "Failures" not in result
        assert "Warnings" not in result
        assert "Info" not in result

    def test_ends_with_newline(self) -> None:
        report = _make_report(status="pass", files_checked=3)
        result = format_detailed(report, color=False)
        assert result.endswith("\n")

    def test_skips_empty_severity_groups(self) -> None:
        issues = [
            _make_issue(severity="fail", file="a.md", issue="fail issue"),
        ]
        report = _make_report(status="fail", issues=issues)
        result = format_detailed(report, color=False)
        assert "Failures (1)" in result
        assert "Warnings" not in result
        assert "Info" not in result
