"""Tests for wos.formatting — human-readable health report output."""

from __future__ import annotations

from wos.formatting import (
    _colorize,
    _status_line,
    _SEVERITY_ORDER,
)


class TestColorize:
    def test_no_color_returns_plain(self) -> None:
        assert _colorize("FAIL", "fail", color=False) == "FAIL"

    def test_color_wraps_with_ansi(self) -> None:
        result = _colorize("FAIL", "fail", color=True)
        assert result.startswith("\033[")
        assert "FAIL" in result
        assert result.endswith("\033[0m")

    def test_pass_is_green(self) -> None:
        result = _colorize("PASS", "pass", color=True)
        assert "\033[32m" in result  # green

    def test_warn_is_yellow(self) -> None:
        result = _colorize("WARN", "warn", color=True)
        assert "\033[33m" in result  # yellow

    def test_info_is_dim(self) -> None:
        result = _colorize("INFO", "info", color=True)
        assert "\033[2m" in result  # dim


class TestSeverityOrder:
    def test_fail_before_warn_before_info(self) -> None:
        assert _SEVERITY_ORDER["fail"] < _SEVERITY_ORDER["warn"]
        assert _SEVERITY_ORDER["warn"] < _SEVERITY_ORDER["info"]


class TestStatusLine:
    def test_pass_status(self) -> None:
        line = _status_line("pass", 0, 5, color=False)
        assert line == "Health: PASS (0 issues in 5 files)"

    def test_fail_status(self) -> None:
        line = _status_line("fail", 3, 12, color=False)
        assert line == "Health: FAIL (3 issues in 12 files)"

    def test_singular_issue(self) -> None:
        line = _status_line("warn", 1, 1, color=False)
        assert line == "Health: WARN (1 issue in 1 file)"

    def test_color_status(self) -> None:
        line = _status_line("fail", 1, 5, color=True)
        assert "\033[" in line
        assert "FAIL" in line


from wos.formatting import _format_token_budget


class TestFormatTokenBudget:
    def test_summary_one_liner(self) -> None:
        budget = {
            "total_estimated_tokens": 28500,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [
                {"area": "python", "files": 5, "estimated_tokens": 18200},
                {"area": "testing", "files": 1, "estimated_tokens": 2000},
            ],
        }
        result = _format_token_budget(budget, detailed=False, color=False)
        assert result == "Token budget: 28,500 / 40,000"

    def test_detailed_with_areas(self) -> None:
        budget = {
            "total_estimated_tokens": 28500,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [
                {"area": "python", "files": 5, "estimated_tokens": 18200},
                {"area": "testing", "files": 1, "estimated_tokens": 2000},
            ],
        }
        result = _format_token_budget(budget, detailed=True, color=False)
        assert "Token budget: 28,500 / 40,000 (2 areas)" in result
        assert "python" in result
        assert "18,200" in result
        assert "testing" in result

    def test_empty_budget(self) -> None:
        budget = {
            "total_estimated_tokens": 0,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [],
        }
        result = _format_token_budget(budget, detailed=False, color=False)
        assert result == "Token budget: 0 / 40,000"

    def test_over_budget_colored(self) -> None:
        budget = {
            "total_estimated_tokens": 50000,
            "warning_threshold": 40000,
            "over_budget": True,
            "areas": [],
        }
        result = _format_token_budget(budget, detailed=False, color=True)
        assert "\033[33m" in result  # yellow for warn


from wos.formatting import format_summary


def _make_report(
    issues=None,
    status="pass",
    files_checked=5,
):
    """Build a minimal report dict for testing."""
    return {
        "status": status,
        "files_checked": files_checked,
        "issues": issues or [],
        "triggers": [],
        "token_budget": {
            "total_estimated_tokens": 1200,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [],
        },
    }


class TestFormatSummary:
    def test_clean_report(self) -> None:
        report = _make_report()
        result = format_summary(report, color=False)
        assert "Health: PASS (0 issues in 5 files)" in result
        assert "Token budget:" in result

    def test_issues_sorted_by_severity(self) -> None:
        issues = [
            {"file": "b.md", "issue": "info issue", "severity": "info",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "a.md", "issue": "fail issue", "severity": "fail",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "c.md", "issue": "warn issue", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="fail", files_checked=3)
        result = format_summary(report, color=False)
        lines = result.strip().split("\n")
        issue_lines = [
            l for l in lines
            if l.strip().startswith(("FAIL", "WARN", "INFO"))
        ]
        assert len(issue_lines) == 3
        assert "FAIL" in issue_lines[0]
        assert "WARN" in issue_lines[1]
        assert "INFO" in issue_lines[2]

    def test_issues_sorted_by_path_within_severity(self) -> None:
        issues = [
            {"file": "z.md", "issue": "issue z", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "a.md", "issue": "issue a", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=2)
        result = format_summary(report, color=False)
        lines = [
            l for l in result.split("\n") if l.strip().startswith("WARN")
        ]
        assert "a.md" in lines[0]
        assert "z.md" in lines[1]

    def test_no_issues_no_blank_issue_block(self) -> None:
        report = _make_report()
        result = format_summary(report, color=False)
        assert "\n\n\n" not in result


from wos.formatting import format_detailed


class TestFormatDetailed:
    def test_groups_by_severity(self) -> None:
        issues = [
            {"file": "a.md", "issue": "broken", "severity": "fail",
             "validator": "v", "section": None, "suggestion": "Fix it"},
            {"file": "b.md", "issue": "stale", "severity": "info",
             "validator": "v", "section": None, "suggestion": "Review"},
        ]
        report = _make_report(issues=issues, status="fail", files_checked=2)
        result = format_detailed(report, color=False)
        assert "Failures (1)" in result
        assert "Info (1)" in result
        assert "Warnings" not in result

    def test_suggestion_arrow(self) -> None:
        issues = [
            {"file": "a.md", "issue": "bad", "severity": "warn",
             "validator": "v", "section": None, "suggestion": "Fix this"},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=1)
        result = format_detailed(report, color=False)
        assert "\u2192 Fix this" in result

    def test_no_suggestion_no_arrow(self) -> None:
        issues = [
            {"file": "a.md", "issue": "bad", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=1)
        result = format_detailed(report, color=False)
        assert "\u2192" not in result

    def test_multiple_issues_same_file_grouped(self) -> None:
        issues = [
            {"file": "a.md", "issue": "issue 1", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
            {"file": "a.md", "issue": "issue 2", "severity": "warn",
             "validator": "v", "section": None, "suggestion": None},
        ]
        report = _make_report(issues=issues, status="warn", files_checked=1)
        result = format_detailed(report, color=False)
        # File path appears once as a header, both issues underneath
        lines = result.split("\n")
        file_lines = [l for l in lines if "a.md" in l and not l.startswith("    ")]
        assert len(file_lines) == 1

    def test_detailed_token_budget_shows_areas(self) -> None:
        report = _make_report()
        report["token_budget"] = {
            "total_estimated_tokens": 5000,
            "warning_threshold": 40000,
            "over_budget": False,
            "areas": [
                {"area": "python", "files": 3, "estimated_tokens": 5000},
            ],
        }
        result = format_detailed(report, color=False)
        assert "python" in result
        assert "5,000" in result

    def test_clean_report(self) -> None:
        report = _make_report()
        result = format_detailed(report, color=False)
        assert "Health: PASS" in result
        assert "Failures" not in result
