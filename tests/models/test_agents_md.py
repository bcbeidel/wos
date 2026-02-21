"""Tests for AgentsMd entity."""
from __future__ import annotations

from wos.models.agents_md import AgentsMd
from wos.models.validation_issue import ValidationIssue


class TestAgentsMd:
    def test_from_template(self):
        agents = AgentsMd.from_template("AGENTS.md")
        assert isinstance(agents, AgentsMd)
        assert "<!-- wos:context:begin -->" in agents.content
        assert "<!-- wos:context:end -->" in agents.content

    def test_from_content(self):
        content = (
            "# AGENTS.md\n\n## Context\n\n"
            "<!-- wos:context:begin -->\n"
            "old content\n"
            "<!-- wos:context:end -->\n"
        )
        agents = AgentsMd.from_content("AGENTS.md", content)
        assert agents.path == "AGENTS.md"
        assert agents.content == content

    def test_update_manifest_replaces_between_markers(self):
        agents = AgentsMd.from_template("AGENTS.md")
        # Create a mock area with a manifest entry
        from wos.models.context_area import ContextArea
        area = ContextArea(name="testing")
        updated = agents.update_manifest([area])
        assert isinstance(updated, AgentsMd)
        assert "Testing" in updated.content
        assert "<!-- wos:context:begin -->" in updated.content
        assert "<!-- wos:context:end -->" in updated.content

    def test_update_manifest_empty_areas(self):
        agents = AgentsMd.from_template("AGENTS.md")
        updated = agents.update_manifest([])
        assert "<!-- wos:context:begin -->" in updated.content
        assert "<!-- wos:context:end -->" in updated.content

    def test_update_manifest_does_not_mutate_original(self):
        agents = AgentsMd.from_template("AGENTS.md")
        original_content = agents.content
        from wos.models.context_area import ContextArea
        area = ContextArea(name="testing")
        updated = agents.update_manifest([area])
        # Original should be unchanged
        assert agents.content == original_content
        # Updated should differ
        assert updated.content != original_content

    def test_update_manifest_preserves_content_outside_markers(self):
        content = (
            "# My Custom AGENTS.md\n\n"
            "Some intro text.\n\n"
            "## Context\n\n"
            "<!-- wos:context:begin -->\n"
            "old manifest\n"
            "<!-- wos:context:end -->\n\n"
            "## Other Section\n\n"
            "Keep this.\n"
        )
        agents = AgentsMd.from_content("AGENTS.md", content)
        updated = agents.update_manifest([])
        assert "My Custom AGENTS.md" in updated.content
        assert "Some intro text." in updated.content
        assert "Other Section" in updated.content
        assert "Keep this." in updated.content

    def test_to_markdown(self):
        agents = AgentsMd.from_template("AGENTS.md")
        assert agents.to_markdown() == agents.content

    def test_validate_self_valid(self):
        agents = AgentsMd.from_template("AGENTS.md")
        assert agents.validate_self() == []

    def test_validate_self_missing_markers(self):
        agents = AgentsMd.from_content("AGENTS.md", "# AGENTS.md\n\nNo markers.\n")
        issues = agents.validate_self()
        assert len(issues) > 0
        assert any("marker" in i.issue.lower() for i in issues)

    def test_validate_self_empty_content(self):
        agents = AgentsMd.from_content("AGENTS.md", "")
        issues = agents.validate_self()
        assert len(issues) > 0
        assert any("empty" in i.issue.lower() for i in issues)

    def test_validate_self_returns_validation_issues(self):
        agents = AgentsMd.from_content("AGENTS.md", "no markers")
        issues = agents.validate_self()
        for issue in issues:
            assert isinstance(issue, ValidationIssue)

    def test_is_valid(self):
        agents = AgentsMd.from_template("AGENTS.md")
        assert agents.is_valid is True

    def test_is_valid_false(self):
        agents = AgentsMd.from_content("AGENTS.md", "no markers")
        assert agents.is_valid is False

    def test_str(self):
        agents = AgentsMd.from_template("AGENTS.md")
        assert "AGENTS.md" in str(agents) or "AgentsMd" in str(agents)

    def test_repr(self):
        agents = AgentsMd.from_template("AGENTS.md")
        assert "AgentsMd" in repr(agents)

    def test_to_json_round_trip(self):
        agents = AgentsMd.from_template("AGENTS.md")
        data = agents.to_json()
        restored = AgentsMd.from_json(data)
        assert restored.path == agents.path
        assert restored.content == agents.content

    def test_to_json_keys(self):
        agents = AgentsMd.from_template("AGENTS.md")
        data = agents.to_json()
        assert "path" in data
        assert "content" in data

    def test_update_manifest_adds_markers_if_missing(self):
        """When content has no markers, update_manifest adds a ## Context section."""
        agents = AgentsMd.from_content("AGENTS.md", "# AGENTS.md\n\nSome content.\n")
        from wos.models.context_area import ContextArea
        area = ContextArea(name="testing")
        updated = agents.update_manifest([area])
        assert "<!-- wos:context:begin -->" in updated.content
        assert "<!-- wos:context:end -->" in updated.content
        assert "Testing" in updated.content

    def test_builder(self):
        from tests.builders import make_agents_md
        agents = make_agents_md()
        assert isinstance(agents, AgentsMd)
        assert agents.is_valid is True

    def test_builder_with_overrides(self):
        from tests.builders import make_agents_md
        agents = make_agents_md(path="custom/AGENTS.md")
        assert agents.path == "custom/AGENTS.md"
