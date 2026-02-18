"""Tests for wos.scaffold — project scaffolding.

All tests use tmp_path for filesystem operations.
"""

from __future__ import annotations

from pathlib import Path

from wos.document_types import parse_document
from wos.scaffold import (
    normalize_area_name,
    scaffold_area,
    scaffold_project,
)

# ── normalize_area_name ──────────────────────────────────────────


class TestNormalizeAreaName:
    def test_lowercase_hyphenated(self) -> None:
        assert normalize_area_name("Python Basics") == "python-basics"

    def test_uppercase(self) -> None:
        assert normalize_area_name("API Design") == "api-design"

    def test_underscores(self) -> None:
        assert normalize_area_name("my_area") == "my-area"

    def test_mixed_separators(self) -> None:
        assert normalize_area_name("my_area name") == "my-area-name"

    def test_already_normalized(self) -> None:
        assert normalize_area_name("python-basics") == "python-basics"

    def test_strips_whitespace(self) -> None:
        assert normalize_area_name("  python  ") == "python"

    def test_removes_special_chars(self) -> None:
        assert normalize_area_name("C++ Basics!") == "c-basics"

    def test_collapses_hyphens(self) -> None:
        assert normalize_area_name("a--b---c") == "a-b-c"


# ── scaffold_project ─────────────────────────────────────────────


class TestScaffoldProject:
    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        result = scaffold_project(
            str(tmp_path), ["python", "testing"]
        )

        assert (tmp_path / "context").is_dir()
        assert (tmp_path / "context" / "python").is_dir()
        assert (tmp_path / "context" / "testing").is_dir()
        assert (tmp_path / "artifacts" / "research").is_dir()
        assert (tmp_path / "artifacts" / "plans").is_dir()
        assert len(result["created"]) > 0

    def test_creates_overview_files(self, tmp_path: Path) -> None:
        scaffold_project(str(tmp_path), ["python", "testing"])

        py_overview = tmp_path / "context" / "python" / "_overview.md"
        test_overview = tmp_path / "context" / "testing" / "_overview.md"
        assert py_overview.exists()
        assert test_overview.exists()

    def test_overview_has_valid_frontmatter(self, tmp_path: Path) -> None:
        scaffold_project(str(tmp_path), ["python"])

        overview = tmp_path / "context" / "python" / "_overview.md"
        content = overview.read_text(encoding="utf-8")
        doc = parse_document("context/python/_overview.md", content)
        assert doc.frontmatter.document_type == "overview"

    def test_normalizes_area_names(self, tmp_path: Path) -> None:
        scaffold_project(str(tmp_path), ["Python Basics"])

        assert (tmp_path / "context" / "python-basics").is_dir()
        assert (
            tmp_path / "context" / "python-basics" / "_overview.md"
        ).exists()

    def test_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        # First scaffold
        scaffold_project(str(tmp_path), ["python"])
        overview = tmp_path / "context" / "python" / "_overview.md"
        overview.read_text(encoding="utf-8")  # confirm exists

        # Modify the file
        overview.write_text("custom content", encoding="utf-8")

        # Second scaffold
        result = scaffold_project(str(tmp_path), ["python"])

        # File should be preserved
        assert overview.read_text(encoding="utf-8") == "custom content"
        assert "context/python/_overview.md" in result["skipped"]

    def test_two_areas_creates_two_overviews(
        self, tmp_path: Path
    ) -> None:
        scaffold_project(str(tmp_path), ["alpha", "beta"])

        overviews = list(
            (tmp_path / "context").glob("*/_overview.md")
        )
        assert len(overviews) == 2

    def test_reports_created_files(self, tmp_path: Path) -> None:
        result = scaffold_project(str(tmp_path), ["python"])
        assert any("python" in f for f in result["created"])


# ── scaffold_area ────────────────────────────────────────────────


class TestScaffoldArea:
    def test_creates_area_directory(self, tmp_path: Path) -> None:
        scaffold_area(str(tmp_path), "python")
        assert (tmp_path / "context" / "python").is_dir()

    def test_creates_overview(self, tmp_path: Path) -> None:
        scaffold_area(str(tmp_path), "python")
        assert (
            tmp_path / "context" / "python" / "_overview.md"
        ).exists()

    def test_overview_valid_frontmatter(self, tmp_path: Path) -> None:
        scaffold_area(
            str(tmp_path), "python", "Python programming essentials"
        )
        overview = tmp_path / "context" / "python" / "_overview.md"
        content = overview.read_text(encoding="utf-8")
        doc = parse_document("context/python/_overview.md", content)
        assert doc.frontmatter.document_type == "overview"
        assert "Python programming essentials" in doc.frontmatter.description

    def test_custom_description(self, tmp_path: Path) -> None:
        scaffold_area(
            str(tmp_path),
            "api-design",
            "API design patterns and best practices",
        )
        overview = tmp_path / "context" / "api-design" / "_overview.md"
        content = overview.read_text(encoding="utf-8")
        assert "API design patterns" in content

    def test_normalizes_name(self, tmp_path: Path) -> None:
        scaffold_area(str(tmp_path), "Python Basics")
        assert (tmp_path / "context" / "python-basics").is_dir()

    def test_does_not_overwrite(self, tmp_path: Path) -> None:
        scaffold_area(str(tmp_path), "python")
        overview = tmp_path / "context" / "python" / "_overview.md"
        overview.write_text("custom", encoding="utf-8")

        result = scaffold_area(str(tmp_path), "python")
        assert overview.read_text(encoding="utf-8") == "custom"
        assert "context/python/_overview.md" in result["skipped"]

    def test_returns_created_list(self, tmp_path: Path) -> None:
        result = scaffold_area(str(tmp_path), "python")
        assert "context/python/_overview.md" in result["created"]
        assert len(result["skipped"]) == 0
