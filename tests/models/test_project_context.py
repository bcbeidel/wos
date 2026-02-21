"""Tests for ProjectContext aggregate root."""
from __future__ import annotations

from tests.builders import (
    make_agents_md,
    make_claude_md,
    make_project_context,
    make_rules_file,
)
from wos.models.context_area import ContextArea
from wos.models.project_context import ProjectContext
from wos.models.validation_issue import ValidationIssue


class TestProjectContextProtocol:
    def test_str_empty(self):
        ctx = make_project_context()
        result = str(ctx)
        assert "ProjectContext" in result
        assert "0 areas" in result

    def test_str_with_areas(self):
        ctx = make_project_context(areas=[ContextArea(name="testing")])
        result = str(ctx)
        assert "1 area" in result

    def test_repr(self):
        ctx = make_project_context()
        assert "ProjectContext" in repr(ctx)
        assert ctx.root in repr(ctx)

    def test_len_empty(self):
        ctx = make_project_context()
        assert len(ctx) == 0

    def test_len_with_areas(self):
        ctx = make_project_context(areas=[ContextArea(name="testing")])
        assert len(ctx) == 1

    def test_len_multiple_areas(self):
        areas = [ContextArea(name="a"), ContextArea(name="b"), ContextArea(name="c")]
        ctx = make_project_context(areas=areas)
        assert len(ctx) == 3

    def test_iter(self):
        areas = [ContextArea(name="a"), ContextArea(name="b")]
        ctx = make_project_context(areas=areas)
        assert list(ctx) == areas

    def test_iter_empty(self):
        ctx = make_project_context()
        assert list(ctx) == []

    def test_contains_by_name(self):
        ctx = make_project_context(areas=[ContextArea(name="testing")])
        assert "testing" in ctx
        assert "unknown" not in ctx

    def test_contains_by_object(self):
        area = ContextArea(name="testing")
        ctx = make_project_context(areas=[area])
        assert area in ctx

    def test_contains_object_not_present(self):
        area = ContextArea(name="testing")
        other = ContextArea(name="other")
        ctx = make_project_context(areas=[area])
        assert other not in ctx


class TestProjectContextValidation:
    def test_validate_self_empty(self):
        ctx = make_project_context()
        issues = ctx.validate_self()
        assert isinstance(issues, list)
        # Empty context should have no issues
        for issue in issues:
            assert isinstance(issue, ValidationIssue)

    def test_is_valid_property(self):
        ctx = make_project_context()
        assert isinstance(ctx.is_valid, bool)

    def test_is_valid_empty_is_true(self):
        ctx = make_project_context()
        assert ctx.is_valid is True

    def test_validate_self_delegates_to_areas(self):
        # An area with a bad name should produce validation issues
        area = ContextArea(name="BAD_NAME")
        ctx = make_project_context(areas=[area])
        issues = ctx.validate_self()
        area_issues = [i for i in issues if "BAD_NAME" in i.issue]
        assert len(area_issues) > 0

    def test_validate_self_delegates_to_agents_md(self):
        # AgentsMd with no markers should produce issues
        agents = make_agents_md(content="no markers here")
        ctx = make_project_context(agents_md=agents)
        issues = ctx.validate_self()
        agents_issues = [
            i for i in issues
            if "markers" in i.issue.lower() or "AGENTS" in i.issue
        ]
        assert len(agents_issues) > 0

    def test_validate_self_delegates_to_claude_md(self):
        # ClaudeMd without @AGENTS.md ref should produce issues
        claude = make_claude_md(content="no agents ref here")
        ctx = make_project_context(claude_md=claude)
        issues = ctx.validate_self()
        claude_issues = [
            i for i in issues
            if "AGENTS" in i.issue or "agents" in i.issue.lower()
        ]
        assert len(claude_issues) > 0

    def test_validate_self_delegates_to_rules_file(self):
        # RulesFile with empty content should produce issues
        rules = make_rules_file(content="")
        ctx = make_project_context(rules_file=rules)
        issues = ctx.validate_self()
        rules_issues = [
            i for i in issues
            if "rules" in i.issue.lower() or "Rules" in i.issue
        ]
        assert len(rules_issues) > 0

    def test_validate_self_valid_agents_md(self):
        # Valid AgentsMd should produce no issues from agents
        agents = make_agents_md()  # default has markers
        ctx = make_project_context(agents_md=agents)
        issues = ctx.validate_self()
        agents_issues = [
            i for i in issues
            if "AGENTS" in i.issue or "markers" in i.issue.lower()
        ]
        assert len(agents_issues) == 0

    def test_validate_self_valid_claude_md(self):
        # Valid ClaudeMd should produce no issues from claude_md
        claude = make_claude_md()  # default has @AGENTS.md
        ctx = make_project_context(claude_md=claude)
        issues = ctx.validate_self()
        claude_issues = [
            i for i in issues
            if "AGENTS" in i.issue or "agents" in i.issue.lower()
        ]
        assert len(claude_issues) == 0

    def test_validate_self_aggregates_all_issues(self):
        # Multiple invalid owned objects: issues from all should be present
        area = ContextArea(name="BAD_NAME")
        agents = make_agents_md(content="no markers")
        claude = make_claude_md(content="no ref")
        rules = make_rules_file(content="")
        ctx = make_project_context(
            areas=[area],
            agents_md=agents,
            claude_md=claude,
            rules_file=rules,
        )
        issues = ctx.validate_self()
        # Should have issues from area, agents, claude, and rules
        assert len(issues) >= 4

    def test_validate_self_deep_flag_passed(self):
        # deep flag should propagate (even if it does nothing extra for now)
        ctx = make_project_context()
        issues = ctx.validate_self(deep=True)
        assert isinstance(issues, list)


class TestProjectContextSerialization:
    def test_to_json_empty(self):
        ctx = make_project_context()
        data = ctx.to_json()
        assert isinstance(data, dict)
        assert "root" in data
        assert "areas" in data
        assert data["root"] == "/tmp/test-project"
        assert data["areas"] == []

    def test_to_json_with_areas(self):
        ctx = make_project_context(areas=[ContextArea(name="testing")])
        data = ctx.to_json()
        assert len(data["areas"]) == 1
        assert data["areas"][0]["name"] == "testing"

    def test_to_json_with_agents_md(self):
        agents = make_agents_md()
        ctx = make_project_context(agents_md=agents)
        data = ctx.to_json()
        assert data["agents_md"] is not None
        assert "path" in data["agents_md"]

    def test_to_json_with_claude_md(self):
        claude = make_claude_md()
        ctx = make_project_context(claude_md=claude)
        data = ctx.to_json()
        assert data["claude_md"] is not None
        assert "path" in data["claude_md"]

    def test_to_json_with_rules_file(self):
        rules = make_rules_file()
        ctx = make_project_context(rules_file=rules)
        data = ctx.to_json()
        assert data["rules_file"] is not None
        assert "content" in data["rules_file"]

    def test_to_json_none_fields_excluded(self):
        ctx = make_project_context()
        data = ctx.to_json()
        assert data["agents_md"] is None
        assert data["claude_md"] is None
        assert data["rules_file"] is None

    def test_from_json_round_trip_empty(self):
        ctx = make_project_context()
        data = ctx.to_json()
        restored = ProjectContext.from_json(data)
        assert restored.root == ctx.root
        assert len(restored.areas) == 0
        assert restored.agents_md is None
        assert restored.claude_md is None
        assert restored.rules_file is None

    def test_from_json_round_trip_with_areas(self):
        ctx = make_project_context(areas=[ContextArea(name="testing")])
        data = ctx.to_json()
        restored = ProjectContext.from_json(data)
        assert restored.root == ctx.root
        assert len(restored.areas) == len(ctx.areas)
        assert restored.areas[0].name == "testing"

    def test_from_json_round_trip_with_owned_files(self):
        ctx = make_project_context(
            agents_md=make_agents_md(),
            claude_md=make_claude_md(),
            rules_file=make_rules_file(),
        )
        data = ctx.to_json()
        restored = ProjectContext.from_json(data)
        assert restored.agents_md is not None
        assert restored.claude_md is not None
        assert restored.rules_file is not None
        assert restored.agents_md.path == ctx.agents_md.path
        assert restored.claude_md.path == ctx.claude_md.path


class TestProjectContextTokens:
    def test_get_estimated_tokens_empty(self):
        ctx = make_project_context()
        assert ctx.get_estimated_tokens() == 0

    def test_get_estimated_tokens_with_areas(self):
        area = ContextArea(name="testing")
        ctx = make_project_context(areas=[area])
        # Even an area with no topics should return >= 0
        assert ctx.get_estimated_tokens() >= 0

    def test_get_estimated_tokens_sums_areas(self):
        areas = [ContextArea(name="a"), ContextArea(name="b")]
        ctx = make_project_context(areas=areas)
        expected = sum(a.get_estimated_tokens() for a in areas)
        assert ctx.get_estimated_tokens() == expected


class TestProjectContextBuilder:
    def test_builder_default(self):
        ctx = make_project_context()
        assert isinstance(ctx, ProjectContext)
        assert ctx.root == "/tmp/test-project"
        assert ctx.areas == []
        assert ctx.agents_md is None
        assert ctx.claude_md is None
        assert ctx.rules_file is None

    def test_builder_overrides_root(self):
        ctx = make_project_context(root="/custom/path")
        assert ctx.root == "/custom/path"

    def test_builder_overrides_areas(self):
        areas = [ContextArea(name="testing")]
        ctx = make_project_context(areas=areas)
        assert len(ctx.areas) == 1
        assert ctx.areas[0].name == "testing"

    def test_builder_overrides_agents_md(self):
        agents = make_agents_md()
        ctx = make_project_context(agents_md=agents)
        assert ctx.agents_md is not None

    def test_builder_overrides_claude_md(self):
        claude = make_claude_md()
        ctx = make_project_context(claude_md=claude)
        assert ctx.claude_md is not None

    def test_builder_overrides_rules_file(self):
        rules = make_rules_file()
        ctx = make_project_context(rules_file=rules)
        assert ctx.rules_file is not None
