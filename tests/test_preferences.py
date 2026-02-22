"""Tests for wos/preferences.py — communication preferences."""

from __future__ import annotations

from pathlib import Path

import pytest

# ── Dimension mapping ────────────────────────────────────────────


class TestDimensionInstruction:
    def test_all_dimensions_have_instructions(self) -> None:
        from wos.preferences import DIMENSION_INSTRUCTIONS, DIMENSIONS

        for dim in DIMENSIONS:
            for level in DIMENSIONS[dim]:
                assert (dim, level) in DIMENSION_INSTRUCTIONS

    def test_instruction_is_nonempty_string(self) -> None:
        from wos.preferences import DIMENSION_INSTRUCTIONS

        for key, instruction in DIMENSION_INSTRUCTIONS.items():
            assert isinstance(instruction, str), f"{key} is not a string"
            assert len(instruction) > 0, f"{key} is empty"


# ── Render preferences ──────────────────────────────────────────


class TestRenderPreferences:
    def test_renders_all_dimensions(self) -> None:
        from wos.preferences import render_preferences

        prefs = {
            "directness": "blunt",
            "verbosity": "terse",
            "depth": "just-answers",
            "expertise": "expert",
            "tone": "casual",
        }
        result = render_preferences(prefs)
        assert "Directness" in result
        assert "Verbosity" in result
        assert "Depth" in result
        assert "Expertise" in result
        assert "Tone" in result

    def test_renders_subset_of_dimensions(self) -> None:
        from wos.preferences import render_preferences

        prefs = {"directness": "blunt", "tone": "formal"}
        result = render_preferences(prefs)
        assert "Directness" in result
        assert "Tone" in result
        # Should not include unspecified dimensions
        assert "Verbosity" not in result

    def test_invalid_dimension_raises(self) -> None:
        from wos.preferences import render_preferences

        with pytest.raises(ValueError, match="Unknown dimension"):
            render_preferences({"nonexistent": "value"})

    def test_invalid_level_raises(self) -> None:
        from wos.preferences import render_preferences

        with pytest.raises(ValueError, match="Unknown level"):
            render_preferences({"directness": "nonexistent"})


# ── Marker replacement ──────────────────────────────────────────


class TestUpdatePreferences:
    def test_creates_file_with_preferences(self, tmp_path: Path) -> None:
        from wos.preferences import update_preferences

        prefs = {"directness": "blunt", "verbosity": "terse"}
        claude_md = tmp_path / "CLAUDE.md"
        update_preferences(str(claude_md), prefs)

        content = claude_md.read_text(encoding="utf-8")
        assert "<!-- wos:communication:begin -->" in content
        assert "<!-- wos:communication:end -->" in content
        assert "Directness" in content

    def test_appends_to_existing_file(self, tmp_path: Path) -> None:
        from wos.preferences import update_preferences

        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nExisting content.\n", encoding="utf-8")

        prefs = {"tone": "formal"}
        update_preferences(str(claude_md), prefs)

        content = claude_md.read_text(encoding="utf-8")
        assert "# My Project" in content
        assert "Existing content." in content
        assert "<!-- wos:communication:begin -->" in content
        assert "Tone" in content

    def test_replaces_existing_preferences(self, tmp_path: Path) -> None:
        from wos.preferences import update_preferences

        claude_md = tmp_path / "CLAUDE.md"
        # Write initial preferences
        update_preferences(str(claude_md), {"directness": "blunt"})
        # Update with different preferences
        update_preferences(str(claude_md), {"directness": "diplomatic"})

        content = claude_md.read_text(encoding="utf-8")
        # Should have exactly one begin and one end marker
        assert content.count("<!-- wos:communication:begin -->") == 1
        assert content.count("<!-- wos:communication:end -->") == 1
        # Should have the updated instruction (not the old one)
        assert "Frame feedback constructively" in content
        assert "State problems and disagreements plainly" not in content

    def test_idempotent(self, tmp_path: Path) -> None:
        from wos.preferences import update_preferences

        claude_md = tmp_path / "CLAUDE.md"
        prefs = {"directness": "blunt"}
        update_preferences(str(claude_md), prefs)
        first = claude_md.read_text(encoding="utf-8")
        update_preferences(str(claude_md), prefs)
        second = claude_md.read_text(encoding="utf-8")
        assert first == second

    def test_preserves_content_around_markers(self, tmp_path: Path) -> None:
        from wos.preferences import (
            COMM_MARKER_BEGIN,
            COMM_MARKER_END,
            update_preferences,
        )

        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            f"# Header\n\nBefore.\n\n"
            f"{COMM_MARKER_BEGIN}\nold stuff\n"
            f"{COMM_MARKER_END}\n\nAfter.\n",
            encoding="utf-8",
        )

        update_preferences(str(claude_md), {"tone": "casual"})

        content = claude_md.read_text(encoding="utf-8")
        assert "# Header" in content
        assert "Before." in content
        assert "After." in content
        assert "old stuff" not in content
        assert "Tone" in content
