"""Tests for sys.path self-insertion in scripts (#59).

Scripts must work when invoked from any working directory, not just the
plugin root. This simulates the installed-plugin scenario where CWD is
the user's project.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestAuditSysPath:
    def test_audit_runs_from_different_cwd(self, tmp_path: Path) -> None:
        """audit.py should work when CWD is not the plugin root."""
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "audit.py"),
                "--root", str(tmp_path), "--no-urls",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        # No ModuleNotFoundError — script should either pass (no content dirs)
        # or fail gracefully (no context/artifacts dir)
        assert "ModuleNotFoundError" not in result.stderr
        assert "No module named" not in result.stderr

    def test_audit_help_from_different_cwd(self, tmp_path: Path) -> None:
        """audit.py --help should work from any directory."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "audit.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "validation checks" in result.stdout.lower()


class TestReindexSysPath:
    def test_reindex_runs_from_different_cwd(self, tmp_path: Path) -> None:
        """reindex.py should work when CWD is not the plugin root."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "reindex.py"), "--root", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert "ModuleNotFoundError" not in result.stderr
        assert "No module named" not in result.stderr

    def test_reindex_help_from_different_cwd(self, tmp_path: Path) -> None:
        """reindex.py --help should work from any directory."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "reindex.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "reindex" in result.stdout.lower() or "_index.md" in result.stdout


class TestValidateSysPath:
    def test_validate_runs_from_different_cwd(self, tmp_path: Path) -> None:
        """validate.py should work when CWD is not the plugin root."""
        doc = tmp_path / "test.md"
        doc.write_text("---\nname: Test\ndescription: A test\n---\nBody\n")
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "validate.py"),
                str(doc), "--root", str(tmp_path), "--no-urls",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert "ModuleNotFoundError" not in result.stderr
        assert "No module named" not in result.stderr
        assert result.returncode == 0
