"""Tests for scripts/experiment_state.py CLI."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch


def _run_cli(*args: str) -> tuple[str, str, int]:
    """Run experiment_state.main() with given CLI args."""
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    exit_code = 0

    with patch.object(sys, "argv", ["experiment_state.py", *args]):
        with patch("sys.stdout", captured_stdout), \
             patch("sys.stderr", captured_stderr):
            try:
                from scripts.experiment_state import main

                main()
            except SystemExit as exc:
                exit_code = exc.code if exc.code is not None else 0

    return captured_stdout.getvalue(), captured_stderr.getvalue(), exit_code


class TestInit:
    def test_creates_state_file(self, tmp_path: Path) -> None:
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Test Experiment",
        )
        assert code == 0
        state_file = tmp_path / "experiment-state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["rigor_tier"] == "exploratory"
        assert data["title"] == "Test Experiment"
        assert data["phases"]["design"]["status"] == "in_progress"

    def test_output_shows_progress(self, tmp_path: Path) -> None:
        stdout, _, _ = _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "pilot", "--title", "Quick Test",
        )
        assert "Quick Test" in stdout
        assert "Pilot" in stdout


class TestStatus:
    def test_shows_progress(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Status Test",
        )
        stdout, _, code = _run_cli("--root", str(tmp_path), "status")
        assert code == 0
        assert "Status Test" in stdout
        assert "Exploratory" in stdout

    def test_missing_state_file_exits_1(self, tmp_path: Path) -> None:
        _, stderr, code = _run_cli("--root", str(tmp_path), "status")
        assert code == 1
        assert "No experiment-state.json" in stderr


class TestAdvance:
    def test_advances_phase(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Advance Test",
        )
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "advance", "--phase", "design",
        )
        assert code == 0
        data = json.loads((tmp_path / "experiment-state.json").read_text())
        assert data["phases"]["design"]["status"] == "complete"
        assert data["phases"]["audit"]["status"] == "in_progress"


class TestCheckGates:
    def test_missing_artifacts_exits_1(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Gate Test",
        )
        _run_cli("--root", str(tmp_path), "advance", "--phase", "design")
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "check-gates",
        )
        assert code == 1
        assert "Missing" in stdout

    def test_satisfied_gates_exits_0(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Gate Test",
        )
        proto = tmp_path / "protocol"
        proto.mkdir()
        (proto / "hypothesis.md").write_text("# H")
        (proto / "design.md").write_text("# D")
        _run_cli("--root", str(tmp_path), "advance", "--phase", "design")
        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "check-gates",
        )
        assert code == 0
        assert "satisfied" in stdout


class TestGenerateManifest:
    def test_creates_manifest_file(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Manifest Test",
        )
        eval_dir = tmp_path / "evaluation"
        eval_dir.mkdir(exist_ok=True)

        stdout, _, code = _run_cli(
            "--root", str(tmp_path), "generate-manifest",
            "--conditions", "gpt-4=OpenAI GPT-4,claude=Anthropic Claude",
            "--seed", "42",
        )
        assert code == 0
        manifest_path = eval_dir / "blinding-manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["blinding_enabled"] is True
        assert data["randomization_seed"] == 42
        assert len(data["conditions"]) == 2

    def test_missing_state_file_exits_1(self, tmp_path: Path) -> None:
        _, stderr, code = _run_cli(
            "--root", str(tmp_path), "generate-manifest",
            "--conditions", "a=A,b=B",
        )
        assert code == 1

    def test_output_confirms_creation(self, tmp_path: Path) -> None:
        _run_cli(
            "--root", str(tmp_path), "init",
            "--tier", "exploratory", "--title", "Test",
        )
        (tmp_path / "evaluation").mkdir(exist_ok=True)
        stdout, _, _ = _run_cli(
            "--root", str(tmp_path), "generate-manifest",
            "--conditions", "a=A,b=B",
        )
        assert "blinding-manifest.json" in stdout
        assert "ALPHA" in stdout or "BRAVO" in stdout
