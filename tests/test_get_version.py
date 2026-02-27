"""Tests for scripts/get_version.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestGetVersion:
    def test_prints_version(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "get_version.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Version should be a semver-like string
        version = result.stdout.strip()
        assert "." in version
