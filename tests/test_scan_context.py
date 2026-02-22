"""Tests for scripts/scan_context.py — progressive context scanner."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)


# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(
    title: str = "Error Handling",
    description: str = "How to handle errors",
) -> str:
    return f"""\
---
document_type: topic
description: {description}
last_updated: 2026-01-15
last_validated: 2026-01-15
sources:
  - url: https://example.com/errors
    title: Error Guide
---

# {title}

## Guidance

Handle errors at the boundary.

## Context

Error handling is critical for robust software.

## In Practice

Use try/except blocks.

## Pitfalls

Don't catch bare exceptions.

## Go Deeper

- [Error Guide](https://example.com/errors)
"""


def _overview_md(
    title: str = "Python Basics",
    description: str = "Fundamentals of Python programming",
) -> str:
    return f"""\
---
document_type: overview
description: {description}
last_updated: 2026-01-15
last_validated: 2026-01-15
---

# {title}

## What This Covers

This area covers Python fundamentals including error handling
and testing best practices for production code.

## Topics

- Error Handling

## Key Sources

- [Python Docs](https://docs.python.org)
"""


def _setup_project(tmp_path: Path) -> None:
    """Create a minimal project with one area containing overview + topic."""
    area = tmp_path / "context" / "python-basics"
    area.mkdir(parents=True)
    (area / "_overview.md").write_text(_overview_md(), encoding="utf-8")
    (area / "error-handling.md").write_text(_topic_md(), encoding="utf-8")


def _run_scanner(tmp_path: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    return subprocess.run(
        [sys.executable, "scripts/scan_context.py"] + args + ["--root", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )


# ── index subcommand ─────────────────────────────────────────────


class TestIndex:
    def test_lists_all_documents(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(tmp_path, ["index"])
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        # Should have 2 documents (overview + topic)
        assert len(lines) == 2

    def test_output_contains_path_and_type(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(tmp_path, ["index"])
        assert "context/python-basics/_overview.md" in result.stdout
        assert "context/python-basics/error-handling.md" in result.stdout
        assert "overview" in result.stdout
        assert "topic" in result.stdout

    def test_filter_by_area(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        # Add a second area
        area2 = tmp_path / "context" / "testing"
        area2.mkdir(parents=True)
        (area2 / "_overview.md").write_text(
            _overview_md(title="Testing", description="Testing practices"),
            encoding="utf-8",
        )
        result = _run_scanner(tmp_path, ["index", "--area", "python-basics"])
        assert result.returncode == 0
        assert "python-basics" in result.stdout
        assert "testing" not in result.stdout

    def test_filter_by_type(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(tmp_path, ["index", "--type", "topic"])
        assert result.returncode == 0
        assert "topic" in result.stdout
        assert "overview" not in result.stdout

    def test_empty_project(self, tmp_path: Path) -> None:
        result = _run_scanner(tmp_path, ["index"])
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ── outline subcommand ───────────────────────────────────────────


class TestOutline:
    def test_shows_section_headings(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(
            tmp_path, ["outline", "context/python-basics/error-handling.md"]
        )
        assert result.returncode == 0
        assert "Guidance" in result.stdout
        assert "Pitfalls" in result.stdout
        assert "words" in result.stdout  # word counts

    def test_file_not_found(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(tmp_path, ["outline", "context/nonexistent.md"])
        assert result.returncode != 0

    def test_shows_title_and_type(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(
            tmp_path, ["outline", "context/python-basics/error-handling.md"]
        )
        assert "Error Handling" in result.stdout
        assert "topic" in result.stdout


# ── extract subcommand ───────────────────────────────────────────


class TestExtract:
    def test_extracts_single_section(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(
            tmp_path,
            ["extract", "context/python-basics/error-handling.md", "Guidance"],
        )
        assert result.returncode == 0
        assert "Handle errors at the boundary" in result.stdout

    def test_extracts_multiple_sections(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(
            tmp_path,
            [
                "extract",
                "context/python-basics/error-handling.md",
                "Guidance",
                "Pitfalls",
            ],
        )
        assert result.returncode == 0
        assert "Handle errors at the boundary" in result.stdout
        assert "bare exceptions" in result.stdout

    def test_section_not_found(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(
            tmp_path,
            ["extract", "context/python-basics/error-handling.md", "Nonexistent"],
        )
        assert result.returncode != 0

    def test_file_not_found(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        result = _run_scanner(
            tmp_path, ["extract", "context/nonexistent.md", "Guidance"]
        )
        assert result.returncode != 0
