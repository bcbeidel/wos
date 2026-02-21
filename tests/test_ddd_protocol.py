"""Tests for DDD protocol on CitedSource and ValidationIssue.

Covers: frozen/immutable, hashable, equality, __str__, __repr__,
to_json, from_json, json round-trip, to_markdown, from_markdown_link,
markdown round-trip, to_yaml_entry, validate_self, is_valid,
builder usage, and WosDomainObject protocol conformance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.builders import make_cited_source, make_validation_issue
from wos.models.core import CitedSource, IssueSeverity, ValidationIssue
from wos.models.protocol import WosDomainObject


# ── Frozen / immutable / hashable / equality ─────────────────────


class TestCitedSourceFrozen:
    def test_immutable_rejects_assignment(self):
        s = make_cited_source()
        with pytest.raises(ValidationError):
            s.url = "https://other.com"

    def test_immutable_rejects_title_assignment(self):
        s = make_cited_source()
        with pytest.raises(ValidationError):
            s.title = "Other Title"

    def test_hashable(self):
        s = make_cited_source()
        assert isinstance(hash(s), int)

    def test_hashable_in_set(self):
        s1 = make_cited_source()
        s2 = make_cited_source()
        assert len({s1, s2}) == 1

    def test_equality_same_values(self):
        s1 = make_cited_source()
        s2 = make_cited_source()
        assert s1 == s2

    def test_equality_different_values(self):
        s1 = make_cited_source(url="https://a.com")
        s2 = make_cited_source(url="https://b.com")
        assert s1 != s2


# ── __str__ and __repr__ ────────────────────────────────────────


class TestCitedSourceStringRepresentations:
    def test_str_is_markdown_link(self):
        s = make_cited_source(title="My Article", url="https://example.com")
        assert str(s) == "[My Article](https://example.com)"

    def test_repr_format(self):
        s = make_cited_source(title="My Article", url="https://example.com")
        assert repr(s) == "CitedSource(url='https://example.com', title='My Article')"


# ── to_json / from_json / round-trip ────────────────────────────


class TestCitedSourceJsonProtocol:
    def test_to_json_returns_dict(self):
        s = make_cited_source()
        data = s.to_json()
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com/article"
        assert data["title"] == "Example Article"

    def test_from_json_returns_cited_source(self):
        data = {"url": "https://example.com", "title": "Test"}
        s = CitedSource.from_json(data)
        assert isinstance(s, CitedSource)
        assert s.url == "https://example.com"
        assert s.title == "Test"

    def test_json_round_trip(self):
        original = make_cited_source()
        restored = CitedSource.from_json(original.to_json())
        assert restored == original


# ── to_markdown / from_markdown_link / round-trip ────────────────


class TestCitedSourceMarkdownProtocol:
    def test_to_markdown_format(self):
        s = make_cited_source(title="Docs", url="https://docs.example.com")
        assert s.to_markdown() == "[Docs](https://docs.example.com)"

    def test_from_markdown_link(self):
        s = CitedSource.from_markdown_link("[Docs](https://docs.example.com)")
        assert s.title == "Docs"
        assert s.url == "https://docs.example.com"

    def test_markdown_round_trip(self):
        original = make_cited_source()
        restored = CitedSource.from_markdown_link(original.to_markdown())
        assert restored == original

    def test_from_markdown_link_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid markdown link"):
            CitedSource.from_markdown_link("not a link")

    def test_from_markdown_link_empty_raises(self):
        with pytest.raises(ValueError, match="Invalid markdown link"):
            CitedSource.from_markdown_link("")

    def test_from_markdown_link_with_special_chars_in_title(self):
        md = "[Python -- Best Practices!](https://example.com)"
        s = CitedSource.from_markdown_link(md)
        assert s.title == "Python -- Best Practices!"
        assert s.url == "https://example.com"


# ── to_yaml_entry ───────────────────────────────────────────────


class TestCitedSourceYamlEntry:
    def test_yaml_entry_format(self):
        s = make_cited_source(url="https://example.com", title="Test Title")
        yaml_str = s.to_yaml_entry()
        assert 'url: "https://example.com"' in yaml_str
        assert 'title: "Test Title"' in yaml_str

    def test_yaml_entry_is_multiline(self):
        s = make_cited_source()
        lines = s.to_yaml_entry().strip().split("\n")
        assert len(lines) == 2


# ── validate_self / is_valid ────────────────────────────────────


class TestCitedSourceValidation:
    def test_validate_self_valid_source(self):
        s = make_cited_source()
        issues = s.validate_self()
        assert issues == []

    def test_validate_self_bad_scheme(self):
        s = make_cited_source(url="ftp://example.com")
        issues = s.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "scheme" in issues[0].issue.lower() or "http" in issues[0].issue.lower()

    def test_validate_self_empty_title(self):
        s = make_cited_source(title="   ")
        issues = s.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "title" in issues[0].issue.lower()

    def test_validate_self_multiple_issues(self):
        s = make_cited_source(url="ftp://example.com", title="   ")
        issues = s.validate_self()
        assert len(issues) == 2

    def test_is_valid_true(self):
        s = make_cited_source()
        assert s.is_valid is True

    def test_is_valid_false_bad_scheme(self):
        s = make_cited_source(url="ftp://example.com")
        assert s.is_valid is False

    def test_is_valid_false_empty_title(self):
        s = make_cited_source(title="")
        assert s.is_valid is False

    def test_validate_self_deep_false_no_network(self):
        """deep=False should not make network calls."""
        s = make_cited_source(url="https://definitely-does-not-exist-12345.invalid")
        # Should return empty list without network I/O
        issues = s.validate_self(deep=False)
        assert issues == []


# ── Builder tests ────────────────────────────────────────────────


class TestCitedSourceBuilder:
    def test_builder_returns_valid(self):
        s = make_cited_source()
        assert isinstance(s, CitedSource)
        assert s.is_valid is True

    def test_builder_override_url(self):
        s = make_cited_source(url="https://custom.com")
        assert s.url == "https://custom.com"
        assert s.title == "Example Article"  # default preserved

    def test_builder_override_title(self):
        s = make_cited_source(title="Custom Title")
        assert s.title == "Custom Title"
        assert s.url == "https://example.com/article"  # default preserved

    def test_builder_override_both(self):
        s = make_cited_source(url="https://custom.com", title="Custom")
        assert s.url == "https://custom.com"
        assert s.title == "Custom"


# ── WosDomainObject protocol conformance ──────────────────────


class TestCitedSourceProtocolConformance:
    def test_isinstance_check(self):
        s = make_cited_source()
        assert isinstance(s, WosDomainObject)

    def test_protocol_str(self):
        s = make_cited_source()
        assert isinstance(str(s), str)

    def test_protocol_repr(self):
        s = make_cited_source()
        assert isinstance(repr(s), str)

    def test_protocol_to_json(self):
        s = make_cited_source()
        assert isinstance(s.to_json(), dict)

    def test_protocol_from_json(self):
        data = {"url": "https://example.com", "title": "Test"}
        s = CitedSource.from_json(data)
        assert isinstance(s, WosDomainObject)

    def test_protocol_validate_self(self):
        s = make_cited_source()
        issues = s.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        s = make_cited_source()
        assert isinstance(s.is_valid, bool)


# ══════════════════════════════════════════════════════════════════
# ValidationIssue DDD protocol tests
# ══════════════════════════════════════════════════════════════════


# ── Frozen / immutable / hashable / equality ─────────────────────


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
