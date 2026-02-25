"""Tests for scripts/audit.py — CLI output formatting (issue #50)."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch


def _run_audit(*args: str, issues: list[dict] | None = None) -> tuple[str, str, int]:
    """Run audit.main() with the given CLI args, returning (stdout, stderr, exitcode).

    If *issues* is provided, validate_project is mocked to return them.
    """
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    exit_code = 0

    mock_target = "wos.validators.validate_project"

    with patch.object(sys, "argv", ["audit.py", *args]):
        with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
            try:
                if issues is not None:
                    with patch(mock_target, return_value=issues):
                        from scripts.audit import main
                        main()
                else:
                    from scripts.audit import main
                    main()
            except SystemExit as exc:
                exit_code = exc.code if exc.code is not None else 0

    return captured_stdout.getvalue(), captured_stderr.getvalue(), exit_code


# ── Relative paths ────────────────────────────────────────────


class TestRelativePaths:
    def test_fail_lines_show_relative_paths(self, tmp_path: Path) -> None:
        """[FAIL] lines should show paths relative to --root, not absolute."""
        root = tmp_path / "project"
        root.mkdir()

        issues = [
            {
                "file": str(root / "artifacts" / "plans" / "_index.md"),
                "issue": "_index.md is out of sync with directory contents",
                "severity": "fail",
            },
        ]

        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)

        # Should NOT contain the absolute path
        assert str(root) not in stdout
        # Should contain the relative path
        assert "artifacts/plans/_index.md" in stdout

    def test_multiple_fail_lines_all_relative(self, tmp_path: Path) -> None:
        """All [FAIL] lines should use relative paths."""
        root = tmp_path / "project"
        root.mkdir()

        issues = [
            {
                "file": str(root / "artifacts" / "plans" / "_index.md"),
                "issue": "_index.md is out of sync",
                "severity": "fail",
            },
            {
                "file": str(root / "context" / "api" / "auth.md"),
                "issue": "Frontmatter 'name' is empty",
                "severity": "fail",
            },
        ]

        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)

        assert "artifacts/plans/_index.md" in stdout
        assert "context/api/auth.md" in stdout
        assert str(root) not in stdout


# ── Summary footer ────────────────────────────────────────────


class TestSummaryFooter:
    def test_single_issue_summary(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()

        issues = [
            {
                "file": str(root / "context" / "bad.md"),
                "issue": "Frontmatter 'name' is empty",
                "severity": "fail",
            },
        ]

        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)

        assert "1 issue found." in stdout

    def test_multiple_issues_summary(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()

        issues = [
            {
                "file": str(root / "a.md"),
                "issue": "Problem A",
                "severity": "fail",
            },
            {
                "file": str(root / "b.md"),
                "issue": "Problem B",
                "severity": "fail",
            },
            {
                "file": str(root / "c.md"),
                "issue": "Problem C",
                "severity": "fail",
            },
        ]

        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)

        assert "3 issues found." in stdout

    def test_no_issues_shows_all_passed(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()

        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=[])

        assert "All checks passed." in stdout

    def test_summary_is_last_line(self, tmp_path: Path) -> None:
        root = tmp_path / "project"
        root.mkdir()

        issues = [
            {
                "file": str(root / "a.md"),
                "issue": "Problem",
                "severity": "fail",
            },
        ]

        stdout, _, _ = _run_audit("--root", str(root), "--no-urls", issues=issues)

        lines = stdout.strip().splitlines()
        assert lines[-1] == "1 issue found."


# ── Warning suppression ──────────────────────────────────────


class TestWarningSuppression:
    def test_no_python_warnings_in_stderr(self, tmp_path: Path) -> None:
        """Python warnings (e.g. urllib3) should not appear in stderr."""
        import warnings

        root = tmp_path / "project"
        root.mkdir()

        def mock_validate(*_args, **_kwargs):
            # Simulate the kind of warning urllib3 emits
            warnings.warn("NotOpenSSLWarning: test warning", stacklevel=1)
            return []

        with patch("wos.validators.validate_project", side_effect=mock_validate):
            _, stderr, _ = _run_audit("--root", str(root), "--no-urls")

        assert "Warning" not in stderr
        assert "warning" not in stderr


# ── JSON output unchanged ────────────────────────────────────


class TestJsonOutput:
    def test_json_output_unchanged(self, tmp_path: Path) -> None:
        """--json should produce the same structure, no summary footer."""
        root = tmp_path / "project"
        root.mkdir()

        issues = [
            {
                "file": str(root / "a.md"),
                "issue": "Problem",
                "severity": "fail",
            },
        ]

        stdout, _, _ = _run_audit(
            "--root", str(root), "--no-urls", "--json", issues=issues
        )

        parsed = json.loads(stdout)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["file"] == str(root / "a.md")
        assert parsed[0]["issue"] == "Problem"
        # No summary footer in JSON output
        assert "issues found" not in stdout


# ── Fix output uses relative paths ───────────────────────────


class TestFixOutput:
    def test_fix_messages_use_relative_paths(self, tmp_path: Path) -> None:
        """--fix stderr messages should also show relative paths."""
        root = tmp_path / "project"
        idx_dir = root / "artifacts" / "plans"
        idx_dir.mkdir(parents=True)
        idx_file = idx_dir / "_index.md"
        idx_file.write_text("")

        issues = [
            {
                "file": str(idx_file),
                "issue": "_index.md is out of sync with directory contents",
                "severity": "fail",
            },
        ]

        with patch("wos.validators.validate_project", return_value=issues):
            _, stderr, _ = _run_audit("--root", str(root), "--no-urls", "--fix")

        assert str(root) not in stderr
        assert "artifacts/plans/_index.md" in stderr
