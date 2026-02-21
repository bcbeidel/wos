"""Tests for wos.models.health_report — HealthReport model."""

from __future__ import annotations

from wos.models.core import IssueSeverity, ValidationIssue
from wos.models.health_report import HealthReport


# ── Helpers ──────────────────────────────────────────────────────


def _issue(
    *,
    severity: str = "fail",
    file: str = "context/python/topic.md",
    issue: str = "Missing section",
    validator: str = "check_section_presence",
) -> ValidationIssue:
    return ValidationIssue(
        file=file,
        issue=issue,
        severity=IssueSeverity(severity),
        validator=validator,
    )


# ── Status computation ──────────────────────────────────────────


class TestStatus:
    def test_pass_with_no_issues(self) -> None:
        report = HealthReport(files_checked=5, issues=[], triggers=[])
        assert report.status == IssueSeverity.PASS

    def test_fail_with_fail_issue(self) -> None:
        report = HealthReport(
            files_checked=5,
            issues=[_issue(severity="fail")],
            triggers=[],
        )
        assert report.status == IssueSeverity.FAIL

    def test_warn_with_only_warn_issues(self) -> None:
        report = HealthReport(
            files_checked=5,
            issues=[_issue(severity="warn")],
            triggers=[],
        )
        assert report.status == IssueSeverity.WARN

    def test_fail_trumps_warn(self) -> None:
        report = HealthReport(
            files_checked=5,
            issues=[
                _issue(severity="warn"),
                _issue(severity="fail"),
            ],
            triggers=[],
        )
        assert report.status == IssueSeverity.FAIL


# ── Actionable issues ──────────────────────────────────────────


class TestActionableIssues:
    def test_excludes_info(self) -> None:
        report = HealthReport(
            files_checked=3,
            issues=[
                _issue(severity="fail"),
                _issue(severity="info"),
                _issue(severity="warn"),
            ],
            triggers=[],
        )
        actionable = report.actionable_issues
        assert len(actionable) == 2
        severities = {i.severity for i in actionable}
        assert IssueSeverity.INFO not in severities


# ── to_json ─────────────────────────────────────────────────────


class TestToJson:
    def test_json_structure(self) -> None:
        report = HealthReport(
            files_checked=3,
            issues=[_issue()],
            triggers=[{"trigger": "test", "file": "x.md"}],
            token_budget={"total_estimated_tokens": 1000, "over_budget": False},
        )
        data = report.to_json()

        assert data["status"] == "fail"
        assert data["files_checked"] == 3
        assert isinstance(data["issues"], list)
        assert len(data["issues"]) == 1
        assert data["issues"][0]["file"] == "context/python/topic.md"
        assert data["token_budget"]["total_estimated_tokens"] == 1000

    def test_json_pass_status(self) -> None:
        report = HealthReport(files_checked=0, issues=[], triggers=[])
        data = report.to_json()
        assert data["status"] == "pass"


# ── to_summary ──────────────────────────────────────────────────


class TestToSummary:
    def test_pass_summary(self) -> None:
        report = HealthReport(files_checked=5, issues=[], triggers=[])
        summary = report.to_summary()
        assert "5 files" in summary
        assert "pass" in summary.lower() or "0 issues" in summary.lower()

    def test_fail_summary_shows_counts(self) -> None:
        report = HealthReport(
            files_checked=3,
            issues=[
                _issue(severity="fail"),
                _issue(severity="fail", file="other.md"),
                _issue(severity="warn"),
            ],
            triggers=[],
        )
        summary = report.to_summary()
        assert "3 files" in summary
        assert "2" in summary  # 2 fail
        assert "1" in summary  # 1 warn


# ── to_detailed ─────────────────────────────────────────────────


class TestToDetailed:
    def test_includes_issue_details(self) -> None:
        report = HealthReport(
            files_checked=2,
            issues=[
                _issue(
                    severity="fail",
                    issue="Missing required section: Guidance",
                    validator="check_section_presence",
                ),
            ],
            triggers=[],
        )
        detailed = report.to_detailed()
        assert "Missing required section: Guidance" in detailed
        assert "context/python/topic.md" in detailed

    def test_groups_by_severity(self) -> None:
        report = HealthReport(
            files_checked=3,
            issues=[
                _issue(severity="warn", issue="Warn issue"),
                _issue(severity="fail", issue="Fail issue"),
            ],
            triggers=[],
        )
        detailed = report.to_detailed()
        # Fail should appear before warn
        fail_idx = detailed.index("Fail issue")
        warn_idx = detailed.index("Warn issue")
        assert fail_idx < warn_idx

    def test_includes_suggestions(self) -> None:
        report = HealthReport(
            files_checked=1,
            issues=[
                ValidationIssue(
                    file="test.md",
                    issue="Problem found",
                    severity=IssueSeverity.WARN,
                    validator="test_validator",
                    suggestion="Fix it like this",
                ),
            ],
            triggers=[],
        )
        detailed = report.to_detailed()
        assert "Fix it like this" in detailed

    def test_includes_triggers(self) -> None:
        report = HealthReport(
            files_checked=1,
            issues=[],
            triggers=[
                {"trigger": "description_quality", "file": "test.md",
                 "question": "Is desc good?"},
            ],
        )
        detailed = report.to_detailed()
        assert "description_quality" in detailed
