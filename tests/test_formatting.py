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
