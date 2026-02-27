"""Tests for scripts/check_runtime.py — uv run canary."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestCheckRuntimeDirect:
    """Test check_runtime.py when run directly with python3 (no uv)."""

    def test_fails_without_httpx(self, tmp_path: Path) -> None:
        """Without uv, httpx won't be available — script should fail."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_runtime.py")],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        # Should fail because httpx isn't installed in our test env
        output = json.loads(result.stdout)
        assert output["status"] == "fail"
        assert result.returncode == 1

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        """Output should always be valid JSON regardless of success/failure."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_runtime.py")],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        parsed = json.loads(result.stdout)
        assert "status" in parsed


class TestCheckRuntimeHelp:
    def test_help_flag(self, tmp_path: Path) -> None:
        """--help should work and exit 0."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_runtime.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "canary" in result.stdout.lower() or "verify" in result.stdout.lower()
