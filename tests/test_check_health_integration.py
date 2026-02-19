"""Integration tests for health script output (token_budget, source reachability)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


def _write_topic(area_dir: Path, name: str, word_count: int = 50) -> None:
    """Write a minimal valid topic file."""
    words = " ".join(["word"] * word_count)
    content = (
        "---\n"
        "document_type: topic\n"
        f'description: "A topic about {name}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        f"\n# {name.replace('-', ' ').title()}\n\n"
        f"## Guidance\n\n{words}\n\n"
        "## Context\n\nBackground.\n\n"
        "## In Practice\n\nExample.\n\n"
        "## Pitfalls\n\nAvoid this.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )
    (area_dir / f"{name}.md").write_text(content, encoding="utf-8")


def _write_overview(area_dir: Path, area_name: str, topics: list[str]) -> None:
    """Write a minimal valid overview file."""
    topic_list = "\n".join(f"- [{t}]({t}.md)" for t in topics)
    content = (
        "---\n"
        "document_type: overview\n"
        f'description: "Overview of {area_name}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        f"\n# {area_name.replace('-', ' ').title()}\n\n"
        "## What This Covers\n\n"
        "This area covers important concepts that every developer "
        "should understand when working with this technology stack "
        "in production environments.\n\n"
        f"## Topics\n\n{topic_list}\n\n"
        "## Key Sources\n\n- [Source](https://example.com)\n"
    )
    (area_dir / "_overview.md").write_text(content, encoding="utf-8")


def _run_health_script(tmp_path: str) -> subprocess.CompletedProcess:
    """Run the health script as a subprocess with proper PYTHONPATH."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    return subprocess.run(
        [sys.executable, "scripts/check_health.py", "--root", tmp_path, "--json"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )


class TestHealthScriptTokenBudget:
    """Verify token_budget appears in health script JSON output."""

    def test_token_budget_in_output(self, tmp_path: Path):
        """Health script output includes token_budget dict."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script(str(tmp_path))
        report = json.loads(result.stdout)

        assert "token_budget" in report
        budget = report["token_budget"]
        assert "total_estimated_tokens" in budget
        assert "warning_threshold" in budget
        assert "over_budget" in budget
        assert "areas" in budget
        assert isinstance(budget["areas"], list)
        assert budget["areas"][0]["area"] == "python"

    def test_token_budget_only_context_files(self, tmp_path: Path):
        """Artifact files are excluded from token budget."""
        # Create context file
        ctx = tmp_path / "context" / "python"
        ctx.mkdir(parents=True)
        _write_topic(ctx, "error-handling")
        _write_overview(ctx, "python", ["error-handling"])

        # Create artifact file (should NOT appear in budget)
        art = tmp_path / "artifacts" / "research"
        art.mkdir(parents=True)
        research_content = (
            "---\n"
            "document_type: research\n"
            'description: "Research into something"\n'
            "last_updated: 2026-02-17\n"
            "sources:\n"
            '  - url: "https://example.com"\n'
            '    title: "Example"\n'
            "---\n"
            "\n# Research Topic\n\n"
            "## Question\n\nWhat is the answer?\n\n"
            "## Findings\n\nThe finding.\n\n"
            "## Implications\n\nImplied.\n\n"
            "## Sources\n\n- [S](https://example.com)\n"
        )
        (art / "2026-02-17-test-research.md").write_text(
            research_content, encoding="utf-8"
        )

        result = _run_health_script(str(tmp_path))
        report = json.loads(result.stdout)
        budget = report["token_budget"]

        # Only python area, no artifact area
        area_names = [a["area"] for a in budget["areas"]]
        assert area_names == ["python"]


class TestHealthScriptSourceReachability:
    """Verify source URL reachability runs with --tier2."""

    def test_no_reachability_without_tier2(self, tmp_path: Path):
        """Without --tier2, no reachability issues appear."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script(str(tmp_path))
        report = json.loads(result.stdout)
        reachability_issues = [
            i for i in report["issues"]
            if i["validator"] == "check_source_url_reachability"
        ]
        assert len(reachability_issues) == 0

    def test_tier2_flag_runs_reachability(self, tmp_path: Path):
        """--tier2 flag triggers source URL reachability checks."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT
        result = subprocess.run(
            [
                sys.executable, "scripts/check_health.py",
                "--root", str(tmp_path), "--tier2", "--json",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
        )
        report = json.loads(result.stdout)
        # Script completes successfully with --tier2 flag
        assert "issues" in report


def _run_health_script_with_flags(
    tmp_path: str, *flags: str
) -> subprocess.CompletedProcess:
    """Run health script with extra flags."""
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    return subprocess.run(
        [sys.executable, "scripts/check_health.py", "--root", tmp_path, *flags],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )


class TestHealthOutputFormats:
    def test_default_is_text(self, tmp_path: Path) -> None:
        """Default output is human-readable text, not JSON."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path))
        assert result.stdout.startswith("Health:")

    def test_json_flag_preserves_current_behavior(self, tmp_path: Path) -> None:
        """--json outputs valid JSON matching existing schema."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path), "--json")
        report = json.loads(result.stdout)
        assert "status" in report
        assert "files_checked" in report
        assert "issues" in report
        assert "token_budget" in report

    def test_detailed_flag(self, tmp_path: Path) -> None:
        """--detailed outputs grouped text."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path), "--detailed")
        assert result.stdout.startswith("Health:")
        assert "Token budget:" in result.stdout

    def test_no_color_flag(self, tmp_path: Path) -> None:
        """--no-color suppresses ANSI codes."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        result = _run_health_script_with_flags(str(tmp_path), "--no-color")
        assert "\033[" not in result.stdout

    def test_exit_code_unchanged(self, tmp_path: Path) -> None:
        """Exit code 0 for pass, regardless of format."""
        area = tmp_path / "context" / "python"
        area.mkdir(parents=True)
        _write_topic(area, "error-handling")
        _write_overview(area, "python", ["error-handling"])

        text_result = _run_health_script_with_flags(str(tmp_path))
        json_result = _run_health_script_with_flags(str(tmp_path), "--json")
        assert text_result.returncode == 0
        assert json_result.returncode == 0
