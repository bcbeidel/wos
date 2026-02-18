"""Tests for wos.cross_validators — cross-file validators.

Tests use tmp_path for filesystem operations and inline markdown strings.
"""

from __future__ import annotations

from pathlib import Path

from wos.cross_validators import (
    check_link_graph,
    check_manifest_sync,
    check_naming_conventions,
    check_overview_topic_sync,
    run_cross_validators,
)
from wos.discovery import run_discovery
from wos.document_types import parse_document

# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(
    title: str = "Error Handling",
    description: str = "When and how to use exceptions in Python",
    related: str = "",
) -> str:
    related_block = ""
    if related:
        related_block = f"related:\n{related}"
    return (
        "---\n"
        "document_type: topic\n"
        f'description: "{description}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://docs.python.org"\n'
        '    title: "Python Docs"\n'
        f"{related_block}"
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        "## Guidance\n\nContent.\n\n"
        "## Context\n\nContent.\n\n"
        "## In Practice\n\nContent.\n\n"
        "## Pitfalls\n\nContent.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )


def _overview_md(topics_section: str = "- Error Handling\n") -> str:
    return (
        "---\n"
        "document_type: overview\n"
        'description: "Core Python programming concepts and practices"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Python\n"
        "\n"
        "## What This Covers\n"
        "\n"
        "This area covers core Python programming concepts including "
        "error handling, testing, and package management patterns.\n"
        "\n"
        "## Topics\n"
        "\n"
        f"{topics_section}"
        "\n"
        "## Key Sources\n"
        "\n"
        "- Python docs\n"
    )


def _setup_project(
    tmp_path: Path,
    *,
    topics: list[tuple[str, str]] | None = None,
    overview_topics: str = "- Error Handling\n",
    related: str = "",
) -> list:
    """Create a project with context files and return parsed docs."""
    area_dir = tmp_path / "context" / "python"
    area_dir.mkdir(parents=True)

    # Overview
    overview_path = area_dir / "_overview.md"
    overview_path.write_text(
        _overview_md(overview_topics), encoding="utf-8"
    )

    # Topics
    if topics is None:
        topics = [("error-handling.md", "Error Handling")]

    for filename, title in topics:
        (area_dir / filename).write_text(
            _topic_md(title=title, related=related),
            encoding="utf-8",
        )

    # Parse all docs
    docs = []
    for md_file in sorted(area_dir.rglob("*.md")):
        rel = str(md_file.relative_to(tmp_path))
        content = md_file.read_text(encoding="utf-8")
        docs.append(parse_document(rel, content))

    return docs


# ── check_link_graph ─────────────────────────────────────────────


class TestCheckLinkGraph:
    def test_no_related_links(self, tmp_path: Path) -> None:
        docs = _setup_project(tmp_path)
        issues = check_link_graph(docs, str(tmp_path))
        assert len(issues) == 0

    def test_valid_file_link(self, tmp_path: Path) -> None:
        docs = _setup_project(
            tmp_path,
            related='  - "context/python/_overview.md"\n',
        )
        issues = check_link_graph(docs, str(tmp_path))
        assert len(issues) == 0

    def test_broken_file_link(self, tmp_path: Path) -> None:
        docs = _setup_project(
            tmp_path,
            related='  - "context/python/nonexistent.md"\n',
        )
        issues = check_link_graph(docs, str(tmp_path))
        assert len(issues) > 0
        assert all(i["severity"] == "fail" for i in issues)
        assert all(
            i["validator"] == "check_link_graph" for i in issues
        )

    def test_valid_url_link(self, tmp_path: Path) -> None:
        docs = _setup_project(
            tmp_path,
            related='  - "https://example.com/resource"\n',
        )
        issues = check_link_graph(docs, str(tmp_path))
        assert len(issues) == 0

    def test_malformed_url(self, tmp_path: Path) -> None:
        docs = _setup_project(
            tmp_path,
            related='  - "not-a-url-or-file"\n',
        )
        issues = check_link_graph(docs, str(tmp_path))
        # Non-URL, non-existent file → fail
        assert len(issues) > 0
        assert issues[0]["severity"] == "fail"


# ── check_overview_topic_sync ────────────────────────────────────


class TestCheckOverviewTopicSync:
    def test_synced(self, tmp_path: Path) -> None:
        docs = _setup_project(
            tmp_path,
            overview_topics="- Error Handling\n",
        )
        issues = check_overview_topic_sync(docs, str(tmp_path))
        assert len(issues) == 0

    def test_topic_not_in_overview(self, tmp_path: Path) -> None:
        docs = _setup_project(
            tmp_path,
            topics=[
                ("error-handling.md", "Error Handling"),
                ("testing.md", "Testing"),
            ],
            overview_topics="- Error Handling\n",
        )
        issues = check_overview_topic_sync(docs, str(tmp_path))
        assert len(issues) == 1
        assert issues[0]["severity"] == "fail"
        assert "Testing" in issues[0]["issue"]

    def test_filename_match(self, tmp_path: Path) -> None:
        """Overview can reference topics by filename stem."""
        docs = _setup_project(
            tmp_path,
            overview_topics="- error-handling\n",
        )
        issues = check_overview_topic_sync(docs, str(tmp_path))
        assert len(issues) == 0


# ── check_manifest_sync ─────────────────────────────────────────


class TestCheckManifestSync:
    def test_synced(self, tmp_path: Path) -> None:
        docs = _setup_project(tmp_path)
        run_discovery(str(tmp_path))
        issues = check_manifest_sync(docs, str(tmp_path))
        assert len(issues) == 0

    def test_drifted(self, tmp_path: Path) -> None:
        docs = _setup_project(tmp_path)
        run_discovery(str(tmp_path))

        # Add a new area without running discovery
        new_area = tmp_path / "context" / "testing"
        new_area.mkdir(parents=True)
        overview = new_area / "_overview.md"
        overview.write_text(
            _overview_md(topics_section="- Unit Tests\n"),
            encoding="utf-8",
        )
        new_doc = parse_document(
            "context/testing/_overview.md",
            overview.read_text(encoding="utf-8"),
        )
        docs.append(new_doc)

        issues = check_manifest_sync(docs, str(tmp_path))
        assert len(issues) == 1
        assert issues[0]["severity"] == "warn"

    def test_no_claude_md(self, tmp_path: Path) -> None:
        docs = _setup_project(tmp_path)
        issues = check_manifest_sync(docs, str(tmp_path))
        assert len(issues) == 0


# ── check_naming_conventions ─────────────────────────────────────


class TestCheckNamingConventions:
    def test_valid_names(self, tmp_path: Path) -> None:
        docs = _setup_project(tmp_path)
        issues = check_naming_conventions(docs, str(tmp_path))
        assert len(issues) == 0


# ── run_cross_validators (integration) ───────────────────────────


class TestRunCrossValidators:
    def test_runs_all(self, tmp_path: Path) -> None:
        docs = _setup_project(tmp_path)
        issues = run_cross_validators(docs, str(tmp_path))
        # Should run without errors; specific issues depend on content
        assert isinstance(issues, list)
