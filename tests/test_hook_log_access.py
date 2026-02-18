"""Tests for wos.hook_log_access — PostToolUse hook script."""

from __future__ import annotations

import json
import subprocess
import sys


def _run_hook(stdin_data, cwd=None):
    """Run the hook script with JSON on stdin."""
    result = subprocess.run(
        [sys.executable, "-m", "wos.hook_log_access"],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result


class TestHookNeverCrashes:
    def test_empty_stdin(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "wos.hook_log_access"],
            input="",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_invalid_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "wos.hook_log_access"],
            input="not json",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_missing_fields(self) -> None:
        result = _run_hook({"tool_name": "Read"})
        assert result.returncode == 0


class TestHookFiltering:
    def test_ignores_non_context_files(self, tmp_path) -> None:
        result = _run_hook(
            {
                "tool_input": {
                    "file_path": str(tmp_path / "wos" / "utils.py"),
                },
                "cwd": str(tmp_path),
            },
        )
        assert result.returncode == 0
        log = tmp_path / ".wos" / "utilization" / "log.jsonl"
        assert not log.exists()

    def test_logs_context_files(self, tmp_path) -> None:
        result = _run_hook(
            {
                "tool_input": {
                    "file_path": str(tmp_path / "context" / "area" / "topic.md"),
                },
                "cwd": str(tmp_path),
                "session_id": "test-session",
            },
        )
        assert result.returncode == 0
        log = tmp_path / ".wos" / "utilization" / "log.jsonl"
        assert log.exists()
        entry = json.loads(log.read_text().strip())
        assert entry["file"] == "context/area/topic.md"
        assert entry["context"] == "test-session"

    def test_uses_agent_as_default_context(self, tmp_path) -> None:
        result = _run_hook(
            {
                "tool_input": {
                    "file_path": str(tmp_path / "context" / "a.md"),
                },
                "cwd": str(tmp_path),
            },
        )
        assert result.returncode == 0
        log = tmp_path / ".wos" / "utilization" / "log.jsonl"
        entry = json.loads(log.read_text().strip())
        assert entry["context"] == "agent"
