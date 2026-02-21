"""DDD protocol tests for ValidationIssue.

Covers: frozen/immutable, hashable, equality, __str__, __repr__,
to_json, from_json, json round-trip, to_markdown, validate_self,
is_valid, and WosDomainObject protocol conformance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.builders import make_validation_issue
from wos.models.enums import IssueSeverity
from wos.models.protocol import WosDomainObject
from wos.models.validation_issue import ValidationIssue


class TestValidationIssueProtocol:
    """DDD protocol tests for ValidationIssue."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        vi = make_validation_issue()
        with pytest.raises(ValidationError):
            vi.issue = "changed"

    def test_hashable(self):
        vi = make_validation_issue()
        assert isinstance(hash(vi), int)

    def test_hashable_in_set(self):
        vi1 = make_validation_issue()
        vi2 = make_validation_issue()
        assert len({vi1, vi2}) == 1

    def test_equality_same_values(self):
        vi1 = make_validation_issue()
        vi2 = make_validation_issue()
        assert vi1 == vi2

    def test_equality_different_values(self):
        vi1 = make_validation_issue(issue="Issue A")
        vi2 = make_validation_issue(issue="Issue B")
        assert vi1 != vi2

    # -- __str__ and __repr__ --

    def test_str_format(self):
        vi = make_validation_issue(
            severity=IssueSeverity.WARN,
            file="context/test/example.md",
            issue="Example validation issue",
        )
        assert str(vi) == "[WARN] context/test/example.md: Example validation issue"

    def test_repr_format(self):
        vi = make_validation_issue(
            file="context/test/example.md",
            issue="Example validation issue",
            severity=IssueSeverity.WARN,
            validator="test_validator",
        )
        assert repr(vi) == (
            "ValidationIssue(file='context/test/example.md', "
            "issue='Example validation issue', "
            "severity='warn', validator='test_validator')"
        )

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        vi = make_validation_issue()
        data = vi.to_json()
        assert isinstance(data, dict)
        assert data["file"] == "context/test/example.md"
        assert data["issue"] == "Example validation issue"
        assert data["severity"] == "warn"
        assert data["validator"] == "test_validator"

    def test_from_json_constructs_instance(self):
        data = {
            "file": "context/test/example.md",
            "issue": "Test issue",
            "severity": "warn",
            "validator": "test_validator",
        }
        vi = ValidationIssue.from_json(data)
        assert isinstance(vi, ValidationIssue)
        assert vi.file == "context/test/example.md"
        assert vi.severity == IssueSeverity.WARN

    def test_json_round_trip(self):
        original = make_validation_issue()
        restored = ValidationIssue.from_json(original.to_json())
        assert restored == original

    # -- to_markdown --

    def test_to_markdown_format(self):
        vi = make_validation_issue(
            severity=IssueSeverity.WARN,
            file="context/test/example.md",
            issue="Example validation issue",
        )
        expected = "- **WARN** `context/test/example.md`: Example validation issue"
        assert vi.to_markdown() == expected

    def test_to_markdown_with_suggestion(self):
        vi = make_validation_issue(suggestion="Fix the thing")
        md = vi.to_markdown()
        lines = md.split("\n")
        assert len(lines) == 2
        assert lines[1] == "  - Fix the thing"

    # -- validate_self / is_valid --

    def test_validate_self_valid_issue(self):
        vi = make_validation_issue()
        issues = vi.validate_self()
        assert issues == []

    def test_validate_self_empty_issue_text(self):
        vi = make_validation_issue(issue="   ")
        issues = vi.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "blank" in issues[0].issue.lower() or "issue" in issues[0].issue.lower()

    def test_is_valid_true(self):
        vi = make_validation_issue()
        assert vi.is_valid is True

    def test_is_valid_false_blank_issue(self):
        vi = make_validation_issue(issue="")
        assert vi.is_valid is False

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        vi = make_validation_issue()
        assert isinstance(vi, WosDomainObject)

    def test_protocol_str(self):
        vi = make_validation_issue()
        assert isinstance(str(vi), str)

    def test_protocol_repr(self):
        vi = make_validation_issue()
        assert isinstance(repr(vi), str)

    def test_protocol_to_json(self):
        vi = make_validation_issue()
        assert isinstance(vi.to_json(), dict)

    def test_protocol_from_json(self):
        data = {
            "file": "test.md",
            "issue": "test",
            "severity": "warn",
            "validator": "test",
        }
        vi = ValidationIssue.from_json(data)
        assert isinstance(vi, WosDomainObject)

    def test_protocol_validate_self(self):
        vi = make_validation_issue()
        issues = vi.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        vi = make_validation_issue()
        assert isinstance(vi.is_valid, bool)

    # -- requires_llm field --

    def test_requires_llm_default_false(self):
        issue = make_validation_issue()
        assert issue.requires_llm is False

    def test_requires_llm_explicit_true(self):
        issue = make_validation_issue(requires_llm=True)
        assert issue.requires_llm is True

    def test_to_json_includes_requires_llm(self):
        issue = make_validation_issue(requires_llm=True)
        data = issue.to_json()
        assert data["requires_llm"] is True

    def test_from_json_round_trip_with_requires_llm(self):
        issue = make_validation_issue(requires_llm=True)
        restored = ValidationIssue.from_json(issue.to_json())
        assert restored.requires_llm is True

    def test_to_markdown_llm_review(self):
        issue = make_validation_issue(requires_llm=True, severity=IssueSeverity.INFO)
        md = issue.to_markdown()
        assert "LLM-REVIEW" in md
