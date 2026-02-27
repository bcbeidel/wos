"""Tests for scripts/update_preferences.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestUpdatePreferencesHelp:
    def test_no_args_shows_usage(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "update_preferences.py")],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 1
        assert "Usage" in result.stderr
