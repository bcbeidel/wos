"""HealthReport model — structured output for health checks.

Wraps the check_health.py output into a proper domain object with
multiple rendering methods (JSON, summary text, detailed text).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from wos.models.core import IssueSeverity, ValidationIssue


class HealthReport(BaseModel):
    """Aggregated health check results for a project."""

    files_checked: int
    issues: List[ValidationIssue]
    triggers: List[Dict[str, Any]]
    token_budget: Optional[Dict[str, Any]] = None

    @property
    def status(self) -> IssueSeverity:
        """Overall status derived from issue severities."""
        severities = {i.severity for i in self.issues}
        if IssueSeverity.FAIL in severities:
            return IssueSeverity.FAIL
        if IssueSeverity.WARN in severities:
            return IssueSeverity.WARN
        return IssueSeverity.PASS

    @property
    def actionable_issues(self) -> list[ValidationIssue]:
        """Issues that require action (fail + warn, excluding info)."""
        return [
            i for i in self.issues
            if i.severity in {IssueSeverity.FAIL, IssueSeverity.WARN}
        ]

    # ── Representations ─────────────────────────────────────────

    def to_json(self) -> dict:
        """JSON-serializable dict matching current check_health.py output."""
        result: dict = {
            "status": self.status.value,
            "files_checked": self.files_checked,
            "issues": [i.model_dump(mode="json") for i in self.issues],
            "triggers": self.triggers,
        }
        if self.token_budget is not None:
            result["token_budget"] = self.token_budget
        return result

    def to_summary(self) -> str:
        """One-line summary for quick orientation."""
        fail_count = sum(
            1 for i in self.issues if i.severity == IssueSeverity.FAIL
        )
        warn_count = sum(
            1 for i in self.issues if i.severity == IssueSeverity.WARN
        )
        info_count = sum(
            1 for i in self.issues if i.severity == IssueSeverity.INFO
        )

        parts = [f"{self.files_checked} files checked"]

        issue_parts = []
        if fail_count:
            issue_parts.append(f"{fail_count} fail")
        if warn_count:
            issue_parts.append(f"{warn_count} warn")
        if info_count:
            issue_parts.append(f"{info_count} info")

        if issue_parts:
            parts.append(", ".join(issue_parts))
        else:
            parts.append("0 issues")

        if self.triggers:
            parts.append(f"{len(self.triggers)} triggers")

        return " | ".join(parts)

    def to_detailed(self) -> str:
        """Multi-line detailed report grouped by severity."""
        lines: list[str] = []
        lines.append(f"Health Report: {self.status.value.upper()}")
        lines.append(f"{self.files_checked} files checked")
        lines.append("")

        # Group issues by severity, fail first
        severity_order = [IssueSeverity.FAIL, IssueSeverity.WARN, IssueSeverity.INFO]
        for severity in severity_order:
            severity_issues = [
                i for i in self.issues if i.severity == severity
            ]
            if not severity_issues:
                continue

            lines.append(f"--- {severity.value.upper()} ({len(severity_issues)}) ---")
            for issue in severity_issues:
                lines.append(f"  {issue.file}: {issue.issue}")
                if issue.suggestion:
                    lines.append(f"    -> {issue.suggestion}")
            lines.append("")

        # Triggers section
        if self.triggers:
            lines.append(f"--- TRIGGERS ({len(self.triggers)}) ---")
            for trigger in self.triggers:
                name = trigger.get("trigger", "unknown")
                file = trigger.get("file", "")
                question = trigger.get("question", "")
                lines.append(f"  {file}: {name}")
                if question:
                    lines.append(f"    ? {question}")
            lines.append("")

        return "\n".join(lines)
