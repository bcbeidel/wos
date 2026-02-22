"""Tests for ClaudeMd entity."""
from __future__ import annotations

from wos.models.claude_md import ClaudeMd


class TestClaudeMd:
    def test_from_template(self):
        cmd = ClaudeMd.from_template("CLAUDE.md")
        assert "@AGENTS.md" in cmd.content

    def test_from_content(self):
        content = "# My Project\n\n@AGENTS.md\n"
        cmd = ClaudeMd.from_content("CLAUDE.md", content)
        assert cmd.path == "CLAUDE.md"
        assert cmd.content == content

    def test_ensure_agents_ref_adds_if_missing(self):
        cmd = ClaudeMd.from_content("CLAUDE.md", "# My Project\n")
        updated = cmd.ensure_agents_ref()
        assert "@AGENTS.md" in updated.content
        assert isinstance(updated, ClaudeMd)

    def test_ensure_agents_ref_no_change_if_present(self):
        content = "# My Project\n\n@AGENTS.md\n"
        cmd = ClaudeMd.from_content("CLAUDE.md", content)
        updated = cmd.ensure_agents_ref()
        assert updated.content == content

    def test_strip_old_markers(self):
        content = (
            "# My Project\n\n"
            "## Context\n\n"
            "<!-- wos:context:begin -->\n"
            "old manifest content\n"
            "<!-- wos:context:end -->\n"
            "\n"
            "## Other\n\nStuff.\n"
        )
        cmd = ClaudeMd.from_content("CLAUDE.md", content)
        stripped = cmd.strip_old_markers()
        assert "<!-- wos:context:begin -->" not in stripped.content
        assert "<!-- wos:context:end -->" not in stripped.content
        assert "## Context" not in stripped.content
        assert "## Other" in stripped.content

    def test_strip_old_markers_no_markers(self):
        content = "# My Project\n\nSome content.\n"
        cmd = ClaudeMd.from_content("CLAUDE.md", content)
        stripped = cmd.strip_old_markers()
        assert stripped.content == content

    def test_to_markdown(self):
        cmd = ClaudeMd.from_template("CLAUDE.md")
        assert cmd.to_markdown() == cmd.content

    def test_validate_self_valid(self):
        cmd = ClaudeMd.from_template("CLAUDE.md")
        assert cmd.validate_self() == []

    def test_validate_self_missing_agents_ref(self):
        cmd = ClaudeMd.from_content("CLAUDE.md", "# My Project\n")
        issues = cmd.validate_self()
        assert len(issues) > 0
        assert any("AGENTS.md" in i.issue for i in issues)

    def test_is_valid(self):
        cmd = ClaudeMd.from_template("CLAUDE.md")
        assert cmd.is_valid is True

    def test_str(self):
        cmd = ClaudeMd.from_template("CLAUDE.md")
        assert "CLAUDE.md" in str(cmd) or "ClaudeMd" in str(cmd)

    def test_repr(self):
        cmd = ClaudeMd.from_template("CLAUDE.md")
        assert "ClaudeMd" in repr(cmd)

    def test_to_json_round_trip(self):
        cmd = ClaudeMd.from_template("CLAUDE.md")
        data = cmd.to_json()
        restored = ClaudeMd.from_json(data)
        assert restored.path == cmd.path
        assert restored.content == cmd.content

    def test_builder(self):
        from tests.builders import make_claude_md
        cmd = make_claude_md()
        assert isinstance(cmd, ClaudeMd)
        assert cmd.is_valid is True
