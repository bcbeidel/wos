"""Tests for scripts/validate.py — single-file validation CLI."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch


def _run_validate(*args: str) -> tuple[str, int]:
    """Run validate.main() with the given CLI args, returning (stdout, exitcode)."""
    captured = StringIO()
    exit_code = 0

    with patch.object(sys, "argv", ["validate.py", *args]):
        with patch("sys.stdout", captured):
            try:
                from scripts.validate import main
                main()
            except SystemExit as exc:
                exit_code = exc.code if exc.code is not None else 0

    return captured.getvalue(), exit_code


class TestValidateClean:
    def test_valid_document_passes(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text(
            "---\nname: Test\ndescription: A test doc\n---\nBody\n"
        )
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        assert code == 0
        assert "All checks passed" in stdout

    def test_missing_frontmatter_fails(self, tmp_path: Path) -> None:
        doc = tmp_path / "bad.md"
        doc.write_text("---\nname: Test\n---\nNo description\n")
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        assert code == 1
        assert "FAIL" in stdout

    def test_research_without_sources_fails(self, tmp_path: Path) -> None:
        doc = tmp_path / "research.md"
        doc.write_text(
            "---\nname: Test\ndescription: A test\ntype: research\n---\nBody\n"
        )
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        assert code == 1
        assert "sources" in stdout.lower()

    def test_nonexistent_file_fails(self, tmp_path: Path) -> None:
        stdout, code = _run_validate(
            str(tmp_path / "missing.md"), "--root", str(tmp_path), "--no-urls"
        )
        assert code == 1

    def test_relative_paths_in_output(self, tmp_path: Path) -> None:
        doc = tmp_path / "bad.md"
        doc.write_text("---\nname: Test\n---\nNo description\n")
        stdout, code = _run_validate(str(doc), "--root", str(tmp_path), "--no-urls")
        # Should not contain absolute path
        assert str(tmp_path) not in stdout
