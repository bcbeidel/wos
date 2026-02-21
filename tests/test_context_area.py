"""Tests for wos.models.context_area — ContextArea model.

Tests use tmp_path for filesystem operations and inline markdown strings.
"""

from __future__ import annotations

from pathlib import Path

from wos.models.context_area import ContextArea


# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(
    *,
    title: str = "Error Handling",
    description: str = "When and how to use exceptions in Python",
) -> str:
    return (
        "---\n"
        "document_type: topic\n"
        f'description: "{description}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://docs.python.org"\n'
        '    title: "Python Docs"\n'
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        "## Guidance\n\nUse exceptions for exceptional cases.\n\n"
        "## Context\n\nBackground info.\n\n"
        "## In Practice\n\nExample usage.\n\n"
        "## Pitfalls\n\nCommon mistakes.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )


def _overview_md(
    *,
    description: str = "Core Python programming concepts and best practices",
    topics_section: str = "- Error Handling\n",
) -> str:
    return (
        "---\n"
        "document_type: overview\n"
        f'description: "{description}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Python\n"
        "\n"
        "## What This Covers\n\n"
        "This area covers core Python programming concepts including error handling, "
        "testing, and package management patterns.\n\n"
        "## Topics\n\n"
        f"{topics_section}\n"
        "## Key Sources\n\n- Python docs\n"
    )


def _setup_area(
    tmp_path: Path,
    area: str = "python",
    *,
    with_overview: bool = True,
    overview_topics: str = "- Error Handling\n",
    topics: list[tuple[str, str, str]] | None = None,
) -> None:
    area_dir = tmp_path / "context" / area
    area_dir.mkdir(parents=True, exist_ok=True)

    if with_overview:
        (area_dir / "_overview.md").write_text(
            _overview_md(topics_section=overview_topics), encoding="utf-8"
        )

    if topics is None:
        topics = [(
            "error-handling.md",
            "Error Handling",
            "When and how to use exceptions in Python",
        )]

    for filename, title, desc in topics:
        (area_dir / filename).write_text(
            _topic_md(title=title, description=desc), encoding="utf-8"
        )


# ── ContextArea.from_directory ──────────────────────────────────


class TestFromDirectory:
    def test_parses_overview_and_topics(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")

        assert area.name == "python"
        assert area.overview is not None
        assert area.overview.document_type.value == "overview"
        assert len(area.topics) == 1
        assert area.topics[0].title == "Error Handling"

    def test_area_without_overview(self, tmp_path: Path) -> None:
        _setup_area(tmp_path, with_overview=False)
        area = ContextArea.from_directory(str(tmp_path), "python")

        assert area.overview is None
        assert len(area.topics) == 1

    def test_multiple_topics_sorted(self, tmp_path: Path) -> None:
        _setup_area(
            tmp_path,
            overview_topics="- Error Handling\n- Testing\n",
            topics=[
                ("testing.md", "Testing", "How to test"),
                ("error-handling.md", "Error Handling", "Exceptions"),
            ],
        )
        area = ContextArea.from_directory(str(tmp_path), "python")

        assert len(area.topics) == 2
        assert area.topics[0].title == "Error Handling"
        assert area.topics[1].title == "Testing"

    def test_skips_unparseable_files(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        (tmp_path / "context" / "python" / "bad.md").write_text(
            "no frontmatter", encoding="utf-8"
        )
        area = ContextArea.from_directory(str(tmp_path), "python")
        assert len(area.topics) == 1

    def test_skips_non_md_files(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        (tmp_path / "context" / "python" / "notes.txt").write_text("hi")
        area = ContextArea.from_directory(str(tmp_path), "python")
        assert len(area.topics) == 1


# ── ContextArea.scan_all ────────────────────────────────────────


class TestScanAll:
    def test_empty_context_dir(self, tmp_path: Path) -> None:
        (tmp_path / "context").mkdir()
        areas = ContextArea.scan_all(str(tmp_path))
        assert areas == []

    def test_no_context_dir(self, tmp_path: Path) -> None:
        areas = ContextArea.scan_all(str(tmp_path))
        assert areas == []

    def test_single_area(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        areas = ContextArea.scan_all(str(tmp_path))

        assert len(areas) == 1
        assert areas[0].name == "python"
        assert areas[0].overview is not None
        assert len(areas[0].topics) == 1

    def test_multiple_areas_sorted(self, tmp_path: Path) -> None:
        _setup_area(tmp_path, "typescript")
        _setup_area(tmp_path, "python")
        areas = ContextArea.scan_all(str(tmp_path))

        assert len(areas) == 2
        assert areas[0].name == "python"
        assert areas[1].name == "typescript"

    def test_skips_hidden_directories(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        hidden = tmp_path / "context" / ".hidden"
        hidden.mkdir()
        (hidden / "secret.md").write_text(_topic_md(), encoding="utf-8")
        areas = ContextArea.scan_all(str(tmp_path))
        assert len(areas) == 1
        assert areas[0].name == "python"


# ── Properties ──────────────────────────────────────────────────


class TestProperties:
    def test_display_name(self) -> None:
        area = ContextArea(name="python-basics")
        assert area.display_name == "Python Basics"

    def test_display_name_single_word(self) -> None:
        area = ContextArea(name="python")
        assert area.display_name == "Python"

    def test_overview_path_with_overview(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")
        assert area.overview_path == "context/python/_overview.md"

    def test_overview_path_without_overview(self) -> None:
        area = ContextArea(name="python")
        assert area.overview_path is None

    def test_overview_description(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")
        assert "Python programming" in area.overview_description


# ── to_manifest_entry ───────────────────────────────────────────


class TestToManifestEntry:
    def test_with_overview(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")
        entry = area.to_manifest_entry()

        assert "[Python](context/python/_overview.md)" in entry
        assert "Python programming" in entry

    def test_without_overview(self) -> None:
        area = ContextArea(name="python")
        entry = area.to_manifest_entry()

        assert "[Python](context/python/)" in entry


# ── get_estimated_tokens ────────────────────────────────────────


class TestGetEstimatedTokens:
    def test_aggregates_all_documents(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")
        tokens = area.get_estimated_tokens()

        assert tokens > 0
        # Should be sum of overview + topic tokens
        expected = 0
        if area.overview:
            expected += area.overview.get_estimated_tokens()
        for topic in area.topics:
            expected += topic.get_estimated_tokens()
        assert tokens == expected

    def test_empty_area(self) -> None:
        area = ContextArea(name="empty")
        assert area.get_estimated_tokens() == 0


# ── validate ────────────────────────────────────────────────────


class TestValidate:
    def test_synced_overview_and_topics(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")
        issues = area.validate()
        # No naming issues, overview mentions Error Handling
        sync_issues = [i for i in issues if i.validator == "check_overview_topic_sync"]
        assert len(sync_issues) == 0

    def test_topic_not_in_overview(self, tmp_path: Path) -> None:
        _setup_area(
            tmp_path,
            overview_topics="- Error Handling\n",
            topics=[
                ("error-handling.md", "Error Handling", "Exceptions"),
                ("testing.md", "Testing", "How to test"),
            ],
        )
        area = ContextArea.from_directory(str(tmp_path), "python")
        issues = area.validate()

        sync_issues = [i for i in issues if i.validator == "check_overview_topic_sync"]
        assert len(sync_issues) == 1
        assert "Testing" in sync_issues[0].issue

    def test_no_overview_no_sync_issues(self, tmp_path: Path) -> None:
        _setup_area(tmp_path, with_overview=False)
        area = ContextArea.from_directory(str(tmp_path), "python")
        issues = area.validate()
        sync_issues = [i for i in issues if i.validator == "check_overview_topic_sync"]
        assert len(sync_issues) == 0

    def test_valid_naming(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")
        naming_issues = [
            i for i in area.validate()
            if i.validator == "check_naming_conventions"
        ]
        assert len(naming_issues) == 0


# ── to_index_records ────────────────────────────────────────────


class TestToIndexRecords:
    def test_includes_overview_and_topics(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        area = ContextArea.from_directory(str(tmp_path), "python")
        records = area.to_index_records()

        assert len(records) == 2  # overview + 1 topic
        paths = [r["path"] for r in records]
        assert "context/python/_overview.md" in paths
        assert "context/python/error-handling.md" in paths

    def test_no_overview(self, tmp_path: Path) -> None:
        _setup_area(tmp_path, with_overview=False)
        area = ContextArea.from_directory(str(tmp_path), "python")
        records = area.to_index_records()
        assert len(records) == 1
