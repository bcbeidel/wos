"""Tests for scripts/reindex.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from wiki.agents_md import BEGIN_MARKER, END_MARKER

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _run(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "reindex.py"), "--root", str(root), *extra],
        capture_output=True,
        text=True,
    )


def _make_md(path: Path, name: str = "", description: str = "") -> None:
    fm_lines = ["---", f"name: {name}", f"description: {description}", "---", "Body."]
    path.write_text("\n".join(fm_lines) + "\n", encoding="utf-8")


class TestReindexCreatesIndexFiles:
    def test_creates_index_for_directory_with_md_files(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "context"
        docs.mkdir(parents=True)
        _make_md(docs / "planning.md", name="Planning", description="How we plan")

        result = _run(tmp_path)
        assert result.returncode == 0

        index = docs / "_index.md"
        assert index.exists()
        content = index.read_text()
        assert "| [planning.md](planning.md) | How we plan |" in content

    def test_index_header_uses_relative_path(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "context"
        docs.mkdir(parents=True)
        _make_md(docs / "topic.md", name="Topic", description="A topic")

        _run(tmp_path)

        index = docs / "_index.md"
        content = index.read_text()
        assert "# docs/context" in content

    def test_index_files_sorted_alphabetically(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir(parents=True)
        _make_md(docs / "zebra.md", name="Zebra", description="Last")
        _make_md(docs / "alpha.md", name="Alpha", description="First")
        _make_md(docs / "middle.md", name="Middle", description="Middle")

        _run(tmp_path)

        content = (docs / "_index.md").read_text()
        z_pos = content.index("zebra.md")
        a_pos = content.index("alpha.md")
        m_pos = content.index("middle.md")
        assert a_pos < m_pos < z_pos

    def test_no_index_for_directory_without_md_files(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        (empty / "notes.txt").write_text("not a markdown file")

        _run(tmp_path)

        assert not (empty / "_index.md").exists()

    def test_existing_index_not_counted_as_managed_doc(self, tmp_path: Path) -> None:
        """A directory with only _index.md should not get a new _index.md."""
        docs = tmp_path / "docs"
        docs.mkdir(parents=True)
        (docs / "_index.md").write_text("# existing index\n")
        # No other .md files

        _run(tmp_path)

        # _index.md should not have been replaced with a table
        content = (docs / "_index.md").read_text()
        assert "# existing index" in content
        assert "| File | Description |" not in content


class TestReindexDoesNotTouchWikiIndex:
    def test_wiki_index_untouched_when_wiki_has_only_index(
        self, tmp_path: Path
    ) -> None:
        """wiki/_index.md is the page inventory; reindex must not overwrite it."""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        wiki_index = wiki / "_index.md"
        wiki_index.write_text("# Wiki Index\n\n| Page | Description | File |\n")

        _run(tmp_path)

        # wiki/_index.md should be unchanged (no other .md in wiki/)
        expected = "# Wiki Index\n\n| Page | Description | File |\n"
        assert wiki_index.read_text() == expected


class TestReindexUpdatesAgentsMd:
    def test_updates_areas_table_with_discovered_dirs(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "context"
        docs.mkdir(parents=True)
        _make_md(docs / "topic.md", name="Topic", description="A topic")

        agents = tmp_path / "AGENTS.md"
        agents.write_text(f"# AGENTS.md\n\n{BEGIN_MARKER}\nold\n{END_MARKER}\n")

        result = _run(tmp_path)
        assert result.returncode == 0

        content = agents.read_text()
        assert "docs/context" in content

    def test_preserves_existing_human_descriptions(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "context"
        docs.mkdir(parents=True)
        _make_md(docs / "topic.md", name="Topic", description="A topic")

        human_desc = "How LLM agents plan and execute tasks"
        agents = tmp_path / "AGENTS.md"
        agents.write_text(
            f"# AGENTS.md\n\n"
            f"{BEGIN_MARKER}\n"
            f"### Areas\n"
            f"| Area | Path |\n"
            f"|------|------|\n"
            f"| {human_desc} | docs/context |\n"
            f"{END_MARKER}\n"
        )

        _run(tmp_path)

        content = agents.read_text()
        assert human_desc in content

    def test_new_areas_get_path_as_fallback_description(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "new-area"
        docs.mkdir(parents=True)
        _make_md(docs / "topic.md", name="Topic", description="A topic")

        agents = tmp_path / "AGENTS.md"
        agents.write_text(f"# AGENTS.md\n\n{BEGIN_MARKER}\nold\n{END_MARKER}\n")

        _run(tmp_path)

        content = agents.read_text()
        # New area falls back to path as description
        assert "docs/new-area" in content

    def test_skips_agents_update_when_no_agents_md(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir(parents=True)
        _make_md(docs / "topic.md", name="Topic", description="A topic")

        result = _run(tmp_path)
        assert result.returncode == 0
        assert "skipping areas update" in result.stdout
        assert not (tmp_path / "AGENTS.md").exists()


class TestReindexOutput:
    def test_reports_count_of_indexed_directories(self, tmp_path: Path) -> None:
        for name in ("alpha", "beta"):
            d = tmp_path / "docs" / name
            d.mkdir(parents=True)
            _make_md(d / "doc.md", name="Doc", description="A doc")

        result = _run(tmp_path)
        assert result.returncode == 0
        assert "2 director" in result.stdout  # "directories"
