"""Test builders for WOS domain objects.

Each make_*() function returns a valid domain object with sensible defaults.
Override any field via keyword arguments.
"""
from __future__ import annotations

from wos.models.base_document import BaseDocument
from wos.models.core import CitedSource, DocumentSection, IssueSeverity, ValidationIssue
from wos.models.frontmatter import SectionSpec, SizeBounds
from wos.models.rules_file import RulesFile
from wos.source_verification import ReachabilityResult, VerificationResult


def make_cited_source(**overrides) -> CitedSource:
    defaults = {
        "url": "https://example.com/article",
        "title": "Example Article",
    }
    defaults.update(overrides)
    return CitedSource(**defaults)


def make_validation_issue(**overrides) -> ValidationIssue:
    defaults = {
        "file": "context/test/example.md",
        "issue": "Example validation issue",
        "severity": IssueSeverity.WARN,
        "validator": "test_validator",
    }
    defaults.update(overrides)
    return ValidationIssue(**defaults)


def make_document_section(**overrides) -> DocumentSection:
    defaults = {
        "name": "Guidance",
        "content": "Use these guidelines for effective implementation.",
    }
    defaults.update(overrides)
    return DocumentSection(**defaults)


def make_section_spec(**overrides) -> SectionSpec:
    defaults = {
        "name": "Guidance",
        "position": 1,
    }
    defaults.update(overrides)
    return SectionSpec(**defaults)


def make_size_bounds(**overrides) -> SizeBounds:
    defaults = {
        "min_lines": 10,
        "max_lines": 500,
    }
    defaults.update(overrides)
    return SizeBounds(**defaults)


def make_verification_result(**overrides) -> VerificationResult:
    defaults = {
        "url": "https://example.com",
        "cited_title": "Example",
        "http_status": 200,
        "page_title": "Example Page",
        "title_match": True,
        "action": "ok",
        "reason": "Title matches",
    }
    defaults.update(overrides)
    return VerificationResult(**defaults)


def make_reachability_result(**overrides) -> ReachabilityResult:
    defaults = {
        "url": "https://example.com",
        "http_status": 200,
        "reachable": True,
        "reason": "OK",
        "final_url": "https://example.com",
    }
    defaults.update(overrides)
    return ReachabilityResult(**defaults)


def make_rules_file(**overrides) -> RulesFile:
    """Build a RulesFile value object with sensible defaults."""
    if not overrides:
        return RulesFile.render()
    defaults = {"content": RulesFile.render().content}
    defaults.update(overrides)
    return RulesFile(**defaults)


def make_agents_md(**overrides):
    """Build an AgentsMd entity with sensible defaults."""
    from wos.models.agents_md import AgentsMd
    if not overrides:
        return AgentsMd.from_template("AGENTS.md")
    defaults = {"path": "AGENTS.md", "content": AgentsMd.from_template("AGENTS.md").content}
    defaults.update(overrides)
    return AgentsMd(**defaults)


def make_claude_md(**overrides):
    """Build a ClaudeMd entity with sensible defaults."""
    from wos.models.claude_md import ClaudeMd
    if not overrides:
        return ClaudeMd.from_template("CLAUDE.md")
    defaults = {"path": "CLAUDE.md", "content": ClaudeMd.from_template("CLAUDE.md").content}
    defaults.update(overrides)
    return ClaudeMd(**defaults)


def make_communication_preferences(**overrides):
    """Build a CommunicationPreferences value object with sensible defaults."""
    from wos.models.communication_preferences import CommunicationPreferences
    defaults = {
        "dimensions": {
            "directness": "balanced",
            "verbosity": "moderate",
            "depth": "context-when-useful",
            "expertise": "intermediate",
            "tone": "neutral",
        }
    }
    if "dimensions" in overrides:
        defaults["dimensions"] = overrides["dimensions"]
    else:
        defaults.update(overrides)
    return CommunicationPreferences(**defaults)


def make_project_context(**overrides):
    """Build a ProjectContext aggregate with sensible defaults."""
    from wos.models.project_context import ProjectContext
    defaults = {
        "root": "/tmp/test-project",
        "areas": [],
    }
    defaults.update(overrides)
    return ProjectContext(**defaults)


def make_context_area(**overrides):
    """Build a ContextArea aggregate with sensible defaults."""
    from wos.models.context_area import ContextArea
    defaults = {
        "name": "test-area",
        "overview": None,
        "topics": [],
    }
    defaults.update(overrides)
    return ContextArea(**defaults)


def make_document(**overrides) -> BaseDocument:
    """Build a minimal valid document (note type -- simplest)."""
    from wos.models.parsing import parse_document

    path = overrides.pop("path", "context/testing/example.md")
    content = overrides.pop("content", None)
    if content is None:
        content = (
            "---\n"
            "document_type: note\n"
            'description: "Test document"\n'
            "---\n"
            "\n"
            "# Test Document\n"
            "\n"
            "Some content here.\n"
        )
    return parse_document(path, content)
