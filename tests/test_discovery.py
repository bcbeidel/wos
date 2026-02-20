"""Tests for wos.discovery — the discovery layer.

All tests use inline markdown strings and tmp_path for filesystem operations.
"""

from __future__ import annotations

from pathlib import Path

from wos.discovery import (
    MARKER_BEGIN,
    MARKER_END,
    render_manifest,
    render_rules_file,
    run_discovery,
    scan_context,
    update_agents_md,
    update_claude_md,
    update_rules_file,
)
from wos.models.context_area import ContextArea

# ── Helpers ──────────────────────────────────────────────────────


def _make_area(
    name: str,
    *,
    overview_desc: str | None = None,
    topic_titles: list[str] | None = None,
) -> ContextArea:
    """Build a ContextArea from inline parsed documents (no filesystem)."""
    from wos.document_types import parse_document

    area = ContextArea(name=name)

    if overview_desc is not None:
        md = (
            "---\n"
            "document_type: overview\n"
            f'description: "{overview_desc}"\n'
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            "---\n\n"
            "# Title\n\n"
            "## What This Covers\n\n"
            "Coverage content for this area.\n\n"
            "## Topics\n\n- topic\n\n"
            "## Key Sources\n\n- source\n"
        )
        area.overview = parse_document(f"context/{name}/_overview.md", md)

    if topic_titles:
        for title in topic_titles:
            slug = title.lower().replace(" ", "-")
            area.topics.append(
                parse_document(
                    f"context/{name}/{slug}.md",
                    _topic_md(title=title),
                )
            )

    return area


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
        "## Guidance\n"
        "\n"
        "Use exceptions for exceptional cases.\n"
        "\n"
        "## Context\n"
        "\n"
        "Background info.\n"
        "\n"
        "## In Practice\n"
        "\n"
        "Example usage.\n"
        "\n"
        "## Pitfalls\n"
        "\n"
        "Common mistakes.\n"
        "\n"
        "## Go Deeper\n"
        "\n"
        "More resources.\n"
    )


def _overview_md(
    *,
    description: str = "Core Python programming concepts and best practices",
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
        "## What This Covers\n"
        "\n"
        "This area covers core Python programming concepts including error handling, "
        "testing, and package management patterns.\n"
        "\n"
        "## Topics\n"
        "\n"
        "- Error Handling\n"
        "\n"
        "## Key Sources\n"
        "\n"
        "- Python docs\n"
    )


def _setup_area(
    tmp_path: Path,
    area: str = "python",
    *,
    with_overview: bool = True,
    topics: list[tuple[str, str, str]] | None = None,
) -> None:
    """Create an area directory with optional overview and topics.

    topics: list of (filename, title, description) tuples
    """
    area_dir = tmp_path / "context" / area
    area_dir.mkdir(parents=True, exist_ok=True)

    if with_overview:
        (area_dir / "_overview.md").write_text(
            _overview_md(), encoding="utf-8"
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


# ── scan_context ─────────────────────────────────────────────────


class TestScanContext:
    def test_empty_context_dir(self, tmp_path: Path) -> None:
        (tmp_path / "context").mkdir()
        areas = scan_context(str(tmp_path))
        assert areas == []

    def test_no_context_dir(self, tmp_path: Path) -> None:
        areas = scan_context(str(tmp_path))
        assert areas == []

    def test_single_area_with_overview_and_topic(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        areas = scan_context(str(tmp_path))

        assert len(areas) == 1
        area = areas[0]
        assert area.name == "python"
        assert area.display_name == "Python"
        assert area.overview_path == "context/python/_overview.md"
        assert len(area.topics) == 1
        assert area.topics[0].title == "Error Handling"
        assert area.topics[0].path == "context/python/error-handling.md"

    def test_area_without_overview(self, tmp_path: Path) -> None:
        _setup_area(tmp_path, with_overview=False)
        areas = scan_context(str(tmp_path))

        assert len(areas) == 1
        assert areas[0].overview_path is None

    def test_multiple_areas_sorted(self, tmp_path: Path) -> None:
        _setup_area(tmp_path, "typescript")
        _setup_area(tmp_path, "python")
        areas = scan_context(str(tmp_path))

        assert len(areas) == 2
        assert areas[0].name == "python"
        assert areas[1].name == "typescript"

    def test_multiple_topics_sorted(self, tmp_path: Path) -> None:
        _setup_area(
            tmp_path,
            topics=[
                ("testing.md", "Testing",
                 "How to write and run Python tests"),
                ("error-handling.md", "Error Handling",
                 "When and how to use exceptions in Python"),
            ],
        )
        areas = scan_context(str(tmp_path))
        topics = areas[0].topics

        assert len(topics) == 2
        assert topics[0].title == "Error Handling"
        assert topics[1].title == "Testing"

    def test_skips_unparseable_files(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        # Add a malformed file
        bad = tmp_path / "context" / "python" / "bad.md"
        bad.write_text("no frontmatter here", encoding="utf-8")

        areas = scan_context(str(tmp_path))
        # Should still have the valid topic
        assert len(areas[0].topics) == 1

    def test_skips_hidden_directories(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        (tmp_path / "context" / ".hidden").mkdir()
        (tmp_path / "context" / ".hidden" / "secret.md").write_text(
            _topic_md(), encoding="utf-8"
        )
        areas = scan_context(str(tmp_path))
        assert len(areas) == 1
        assert areas[0].name == "python"

    def test_skips_non_md_files(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        (tmp_path / "context" / "python" / "notes.txt").write_text("hi")
        areas = scan_context(str(tmp_path))
        assert len(areas[0].topics) == 1


# ── render_manifest ──────────────────────────────────────────────


class TestRenderManifest:
    def test_empty_areas(self) -> None:
        assert render_manifest([]) == ""

    def test_single_area_with_overview(self) -> None:
        areas = [
            _make_area(
                "python",
                overview_desc="Python concepts",
                topic_titles=["Error Handling"],
            ),
        ]
        manifest = render_manifest(areas)

        assert "| Area | Description |" in manifest
        assert "[Python](context/python/_overview.md)" in manifest
        assert "Python concepts" in manifest
        # Topics are NOT listed individually in compact format
        assert "Error Handling" not in manifest

    def test_area_without_overview_links_to_directory(self) -> None:
        areas = [
            _make_area("python", topic_titles=["Error Handling"]),
        ]
        manifest = render_manifest(areas)
        assert "[Python](context/python/)" in manifest

    def test_area_without_topics(self) -> None:
        areas = [
            _make_area("python", overview_desc="Python concepts"),
        ]
        manifest = render_manifest(areas)
        assert "[Python](context/python/_overview.md)" in manifest

    def test_multiple_areas_in_order(self) -> None:
        areas = [
            _make_area("python", overview_desc="Python programming concepts"),
            _make_area("typescript", overview_desc="TypeScript development patterns"),
        ]
        manifest = render_manifest(areas)
        assert "| Area | Description |" in manifest
        python_idx = manifest.index("Python")
        ts_idx = manifest.index("Typescript")
        assert python_idx < ts_idx

    def test_compact_format_is_single_table(self) -> None:
        areas = [
            _make_area(
                "python",
                overview_desc="Python concepts",
                topic_titles=["Error Handling"],
            ),
            _make_area("testing", overview_desc="Testing practices"),
        ]
        manifest = render_manifest(areas)
        lines = manifest.strip().split("\n")
        # Header + separator + 2 area rows = 4 lines
        assert len(lines) == 4


# ── update_claude_md ─────────────────────────────────────────────


class TestUpdateClaudeMd:
    def test_creates_file_when_missing(self, tmp_path: Path) -> None:
        target = str(tmp_path / "CLAUDE.md")
        update_claude_md(target, "### Python\n\nSome content")

        content = Path(target).read_text(encoding="utf-8")
        assert "# CLAUDE.md" in content
        assert "## Context" in content
        assert MARKER_BEGIN in content
        assert MARKER_END in content
        assert "### Python" in content

    def test_replaces_between_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text(
            "# My Project\n"
            "\n"
            "## Context\n"
            "\n"
            f"{MARKER_BEGIN}\n"
            "old content\n"
            f"{MARKER_END}\n"
            "\n"
            "## Other Section\n",
            encoding="utf-8",
        )

        update_claude_md(str(target), "### New Content")
        content = target.read_text(encoding="utf-8")

        assert "### New Content" in content
        assert "old content" not in content

    def test_preserves_content_outside_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text(
            "# My Project\n"
            "\n"
            "Important stuff here.\n"
            "\n"
            "## Context\n"
            "\n"
            f"{MARKER_BEGIN}\n"
            "will be replaced\n"
            f"{MARKER_END}\n"
            "\n"
            "## Build & Test\n"
            "\n"
            "```bash\npytest\n```\n",
            encoding="utf-8",
        )

        update_claude_md(str(target), "### Updated")
        content = target.read_text(encoding="utf-8")

        assert "# My Project" in content
        assert "Important stuff here." in content
        assert "## Build & Test" in content
        assert "pytest" in content
        assert "### Updated" in content
        assert "will be replaced" not in content

    def test_adds_context_section_when_no_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text(
            "# My Project\n"
            "\n"
            "Some existing content.\n",
            encoding="utf-8",
        )

        update_claude_md(str(target), "### Python")
        content = target.read_text(encoding="utf-8")

        assert "# My Project" in content
        assert "Some existing content." in content
        assert "## Context" in content
        assert MARKER_BEGIN in content
        assert "### Python" in content

    def test_empty_manifest_between_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text(
            f"# Project\n\n{MARKER_BEGIN}\nold\n{MARKER_END}\n",
            encoding="utf-8",
        )

        update_claude_md(str(target), "")
        content = target.read_text(encoding="utf-8")

        assert MARKER_BEGIN in content
        assert MARKER_END in content
        assert "old" not in content

    def test_preserves_large_existing_file_without_markers(
        self, tmp_path: Path
    ) -> None:
        """Regression test for #3: large CLAUDE.md must not be overwritten."""
        target = tmp_path / "CLAUDE.md"
        lines = [f"Line {i}: important project guidance" for i in range(305)]
        original = "\n".join(lines) + "\n"
        target.write_text(original, encoding="utf-8")

        update_claude_md(str(target), "| Area | Description |")
        content = target.read_text(encoding="utf-8")

        # All original lines preserved
        for i in range(0, 305, 50):
            assert f"Line {i}: important project guidance" in content

        # Context section appended
        assert "## Context" in content
        assert MARKER_BEGIN in content
        assert "| Area | Description |" in content

    def test_warns_on_append_to_existing(
        self, tmp_path: Path, capsys: object
    ) -> None:
        target = tmp_path / "CLAUDE.md"
        target.write_text("# Project\n\nExisting content.\n", encoding="utf-8")

        update_claude_md(str(target), "manifest")
        captured = capsys.readouterr()  # type: ignore[attr-defined]

        assert "exists without markers" in captured.err
        assert "3 existing lines preserved" in captured.err

    def test_warns_on_create_from_template(
        self, tmp_path: Path, capsys: object
    ) -> None:
        target = str(tmp_path / "CLAUDE.md")

        update_claude_md(target, "manifest")
        captured = capsys.readouterr()  # type: ignore[attr-defined]

        assert "creating from template" in captured.err


# ── update_agents_md ─────────────────────────────────────────────


class TestUpdateAgentsMd:
    def test_creates_file_when_missing(self, tmp_path: Path) -> None:
        target = str(tmp_path / "AGENTS.md")
        update_agents_md(target, "### Python\n\nContent")

        content = Path(target).read_text(encoding="utf-8")
        assert "# AGENTS.md" in content
        assert MARKER_BEGIN in content
        assert "### Python" in content

    def test_replaces_between_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "AGENTS.md"
        target.write_text(
            f"# AGENTS.md\n\n{MARKER_BEGIN}\nold\n{MARKER_END}\n",
            encoding="utf-8",
        )

        update_agents_md(str(target), "### New")
        content = target.read_text(encoding="utf-8")

        assert "### New" in content
        assert "old" not in content


# ── render_rules_file ────────────────────────────────────────────


class TestRenderRulesFile:
    def test_under_50_lines(self) -> None:
        rules = render_rules_file()
        lines = rules.strip().split("\n")
        assert len(lines) <= 50, f"Rules file is {len(lines)} lines, expected <= 50"

    def test_contains_document_types(self) -> None:
        rules = render_rules_file()
        assert "topic" in rules
        assert "overview" in rules
        assert "research" in rules
        assert "plan" in rules

    def test_contains_skill_pointers(self) -> None:
        rules = render_rules_file()
        assert "/wos:" in rules


# ── update_rules_file ────────────────────────────────────────────


class TestUpdateRulesFile:
    def test_creates_directory_and_file(self, tmp_path: Path) -> None:
        update_rules_file(str(tmp_path), "# Rules content\n")

        rules_path = tmp_path / ".claude" / "rules" / "wos-context.md"
        assert rules_path.exists()
        assert rules_path.read_text(encoding="utf-8") == "# Rules content\n"


# ── run_discovery (integration) ──────────────────────────────────


class TestRunDiscovery:
    def test_full_pipeline(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        run_discovery(str(tmp_path))

        claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        rules_path = (
            tmp_path / ".claude" / "rules" / "wos-context.md"
        )
        rules = rules_path.read_text(encoding="utf-8")

        # CLAUDE.md has compact manifest with area link
        assert "[Python](context/python/_overview.md)" in claude_md

        # AGENTS.md mirrors CLAUDE.md manifest
        assert "[Python](context/python/_overview.md)" in agents_md

        # Rules file exists and is reasonable
        assert "Document Types" in rules

    def test_idempotent(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)

        run_discovery(str(tmp_path))
        first_claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        first_agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        rules_path = (
            tmp_path / ".claude" / "rules" / "wos-context.md"
        )
        first_rules = rules_path.read_text(encoding="utf-8")

        run_discovery(str(tmp_path))
        second_claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        second_agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        second_rules = rules_path.read_text(encoding="utf-8")

        assert first_claude == second_claude
        assert first_agents == second_agents
        assert first_rules == second_rules

    def test_preserves_existing_claude_md(self, tmp_path: Path) -> None:
        # Create existing CLAUDE.md with custom content
        (tmp_path / "CLAUDE.md").write_text(
            "# My Project\n"
            "\n"
            "Custom instructions here.\n"
            "\n"
            "## Build\n"
            "\n"
            "make build\n",
            encoding="utf-8",
        )

        _setup_area(tmp_path)
        run_discovery(str(tmp_path))

        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "# My Project" in content
        assert "Custom instructions here." in content
        assert "make build" in content
        assert "[Python](context/python/_overview.md)" in content

    def test_empty_context_produces_empty_manifest(self, tmp_path: Path) -> None:
        (tmp_path / "context").mkdir()
        run_discovery(str(tmp_path))

        claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert MARKER_BEGIN in claude_md
        assert MARKER_END in claude_md

    def test_manifest_matches_between_claude_and_agents(self, tmp_path: Path) -> None:
        _setup_area(tmp_path)
        _setup_area(
            tmp_path,
            "testing",
            topics=[(
                "unit-tests.md",
                "Unit Tests",
                "Writing effective unit tests for Python code",
            )],
        )
        run_discovery(str(tmp_path))

        claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

        # Extract manifest content between markers from both files
        def extract_manifest(content: str) -> str:
            begin = content.index(MARKER_BEGIN) + len(MARKER_BEGIN)
            end = content.index(MARKER_END)
            return content[begin:end]

        assert extract_manifest(claude_md) == extract_manifest(agents_md)
