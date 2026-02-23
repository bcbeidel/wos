"""Tests for wos/validators.py — per-file and project-wide validation checks."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from wos.document import Document


# ── Helpers ─────────────────────────────────────────────────────


def _make_doc(**overrides) -> Document:
    """Build a minimal valid Document, applying overrides."""
    defaults = {
        "path": "context/testing/unit-tests.md",
        "name": "Unit Tests",
        "description": "Guide to writing unit tests",
        "content": "# Unit Tests\n\nSome content.\n",
    }
    defaults.update(overrides)
    return Document(**defaults)


def _md(name: str = "Test", description: str = "A test doc", **extra_fm) -> str:
    """Build a minimal markdown string with frontmatter."""
    lines = ["---", f"name: {name}", f"description: {description}"]
    for key, value in extra_fm.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append(f"# {name}")
    lines.append("")
    return "\n".join(lines) + "\n"


# ── check_frontmatter ──────────────────────────────────────────


class TestCheckFrontmatter:
    def test_valid_doc_no_issues(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(name="Valid", description="A valid document")
        issues = check_frontmatter(doc)
        assert issues == []

    def test_empty_name(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(name="")
        issues = check_frontmatter(doc)
        assert len(issues) == 1
        assert issues[0]["severity"] == "fail"
        assert "name" in issues[0]["issue"].lower()
        assert issues[0]["file"] == doc.path

    def test_empty_description(self) -> None:
        from wos.validators import check_frontmatter

        doc = _make_doc(description="")
        issues = check_frontmatter(doc)
        assert len(issues) == 1
        assert issues[0]["severity"] == "fail"
        assert "description" in issues[0]["issue"].lower()
        assert issues[0]["file"] == doc.path


# ── check_research_sources ─────────────────────────────────────


class TestCheckResearchSources:
    def test_research_with_sources_ok(self) -> None:
        from wos.validators import check_research_sources

        doc = _make_doc(
            type="research",
            sources=["https://example.com/source"],
        )
        issues = check_research_sources(doc)
        assert issues == []

    def test_research_without_sources_fail(self) -> None:
        from wos.validators import check_research_sources

        doc = _make_doc(type="research", sources=[])
        issues = check_research_sources(doc)
        assert len(issues) == 1
        assert issues[0]["severity"] == "fail"
        assert "sources" in issues[0]["issue"].lower()

    def test_non_research_without_sources_ok(self) -> None:
        from wos.validators import check_research_sources

        doc = _make_doc(type="topic", sources=[])
        issues = check_research_sources(doc)
        assert issues == []

    def test_no_type_without_sources_ok(self) -> None:
        from wos.validators import check_research_sources

        doc = _make_doc(type=None, sources=[])
        issues = check_research_sources(doc)
        assert issues == []


# ── check_source_urls ──────────────────────────────────────────


class TestCheckSourceUrls:
    def test_all_reachable(self) -> None:
        from wos.url_checker import UrlCheckResult
        from wos.validators import check_source_urls

        doc = _make_doc(sources=["https://example.com/a", "https://example.com/b"])

        mock_results = [
            UrlCheckResult(url="https://example.com/a", status=200, reachable=True),
            UrlCheckResult(url="https://example.com/b", status=200, reachable=True),
        ]
        with patch("wos.validators.check_urls", return_value=mock_results):
            issues = check_source_urls(doc)
        assert issues == []

    def test_unreachable_url(self) -> None:
        from wos.url_checker import UrlCheckResult
        from wos.validators import check_source_urls

        doc = _make_doc(sources=["https://example.com/missing"])

        mock_results = [
            UrlCheckResult(
                url="https://example.com/missing",
                status=404,
                reachable=False,
                reason="HTTP 404",
            ),
        ]
        with patch("wos.validators.check_urls", return_value=mock_results):
            issues = check_source_urls(doc)
        assert len(issues) == 1
        assert issues[0]["severity"] == "fail"
        assert "https://example.com/missing" in issues[0]["issue"]

    def test_no_sources_no_check_called(self) -> None:
        from wos.validators import check_source_urls

        doc = _make_doc(sources=[])

        with patch("wos.validators.check_urls") as mock_check:
            issues = check_source_urls(doc)
        mock_check.assert_not_called()
        assert issues == []


# ── check_related_paths ────────────────────────────────────────


class TestCheckRelatedPaths:
    def test_existing_paths_ok(self, tmp_path: Path) -> None:
        from wos.validators import check_related_paths

        # Create a file on disk
        related_file = tmp_path / "context" / "api" / "auth.md"
        related_file.parent.mkdir(parents=True)
        related_file.write_text("# Auth\n")

        doc = _make_doc(related=["context/api/auth.md"])
        issues = check_related_paths(doc, tmp_path)
        assert issues == []

    def test_missing_path_fail(self, tmp_path: Path) -> None:
        from wos.validators import check_related_paths

        doc = _make_doc(related=["context/api/nonexistent.md"])
        issues = check_related_paths(doc, tmp_path)
        assert len(issues) == 1
        assert issues[0]["severity"] == "fail"
        assert "nonexistent.md" in issues[0]["issue"]

    def test_urls_skipped(self, tmp_path: Path) -> None:
        from wos.validators import check_related_paths

        doc = _make_doc(
            related=[
                "https://github.com/org/repo/issues/42",
                "http://example.com/page",
            ]
        )
        issues = check_related_paths(doc, tmp_path)
        assert issues == []

    def test_no_related_no_issues(self, tmp_path: Path) -> None:
        from wos.validators import check_related_paths

        doc = _make_doc(related=[])
        issues = check_related_paths(doc, tmp_path)
        assert issues == []


# ── check_all_indexes ──────────────────────────────────────────


class TestCheckAllIndexes:
    def test_synced_index(self, tmp_path: Path) -> None:
        from wos.index import generate_index
        from wos.validators import check_all_indexes

        # Create a directory with a file and a synced _index.md
        area = tmp_path / "context" / "testing"
        area.mkdir(parents=True)
        topic = area / "unit-tests.md"
        topic.write_text(
            "---\nname: Unit Tests\ndescription: Unit testing guide\n---\n# Unit Tests\n"
        )
        index = area / "_index.md"
        index.write_text(generate_index(area))
        # Also create a synced index for the context root
        context_dir = tmp_path / "context"
        (context_dir / "_index.md").write_text(generate_index(context_dir))

        issues = check_all_indexes(context_dir)
        assert issues == []

    def test_missing_index(self, tmp_path: Path) -> None:
        from wos.validators import check_all_indexes

        # Create a directory with a file but no _index.md
        area = tmp_path / "context" / "testing"
        area.mkdir(parents=True)
        topic = area / "unit-tests.md"
        topic.write_text(
            "---\nname: Unit Tests\ndescription: Unit testing guide\n---\n# Unit Tests\n"
        )

        issues = check_all_indexes(tmp_path / "context")
        assert len(issues) >= 1
        assert any("missing" in i["issue"].lower() for i in issues)


# ── validate_file ──────────────────────────────────────────────


class TestValidateFile:
    def test_valid_file(self, tmp_path: Path) -> None:
        from wos.validators import validate_file

        md_file = tmp_path / "context" / "testing" / "unit-tests.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text(_md("Unit Tests", "Guide to unit tests"))

        issues = validate_file(md_file, tmp_path, check_urls=False)
        assert issues == []

    def test_file_without_frontmatter(self, tmp_path: Path) -> None:
        from wos.validators import validate_file

        md_file = tmp_path / "context" / "testing" / "bad.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("# No Frontmatter\n\nJust content.\n")

        issues = validate_file(md_file, tmp_path, check_urls=False)
        assert len(issues) == 1
        assert issues[0]["severity"] == "fail"
        assert "parse" in issues[0]["issue"].lower() or "frontmatter" in issues[0]["issue"].lower()


# ── validate_project ───────────────────────────────────────────


class TestValidateProject:
    def test_valid_project(self, tmp_path: Path) -> None:
        from wos.index import generate_index
        from wos.validators import validate_project

        # Set up context area
        area = tmp_path / "context" / "testing"
        area.mkdir(parents=True)
        topic = area / "unit-tests.md"
        topic.write_text(_md("Unit Tests", "Guide to unit tests"))
        # Create synced index for the area
        (area / "_index.md").write_text(generate_index(area))
        # Create synced index for context root
        (tmp_path / "context" / "_index.md").write_text(
            generate_index(tmp_path / "context")
        )

        issues = validate_project(tmp_path, check_urls=False)
        assert issues == []
