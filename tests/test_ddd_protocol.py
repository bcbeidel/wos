"""Tests for DDD protocol on CitedSource, ValidationIssue, DocumentSection,
SectionSpec, SizeBounds, VerificationResult, and ReachabilityResult.

Covers: frozen/immutable, hashable, equality, __str__, __repr__,
to_json, from_json, json round-trip, to_markdown, from_markdown_link,
markdown round-trip, to_yaml_entry, validate_self, is_valid,
builder usage, and WosDomainObject protocol conformance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.builders import (
    make_cited_source,
    make_document_section,
    make_reachability_result,
    make_section_spec,
    make_size_bounds,
    make_validation_issue,
    make_verification_result,
)
from wos.models.core import CitedSource, DocumentSection, IssueSeverity, ValidationIssue
from wos.models.frontmatter import SectionSpec, SizeBounds
from wos.models.protocol import WosDomainObject
from wos.source_verification import ReachabilityResult, VerificationResult


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


# ══════════════════════════════════════════════════════════════════
# DocumentSection DDD protocol tests
# ══════════════════════════════════════════════════════════════════


class TestDocumentSectionProtocol:
    """DDD protocol tests for DocumentSection."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        sec = make_document_section()
        with pytest.raises(ValidationError):
            sec.name = "Changed"

    def test_hashable(self):
        sec = make_document_section()
        assert isinstance(hash(sec), int)

    def test_hashable_in_set(self):
        s1 = make_document_section()
        s2 = make_document_section()
        assert len({s1, s2}) == 1

    def test_equality_same_values(self):
        s1 = make_document_section()
        s2 = make_document_section()
        assert s1 == s2

    def test_equality_different_values(self):
        s1 = make_document_section(name="Guidance")
        s2 = make_document_section(name="Other")
        assert s1 != s2

    # -- __str__ and __repr__ --

    def test_str_format(self):
        sec = make_document_section(name="Guidance", content="word1 word2 word3")
        assert str(sec) == "## Guidance (3 words)"

    def test_repr_format_no_lines(self):
        sec = make_document_section(name="Guidance", content="word1 word2")
        assert repr(sec) == "DocumentSection(name='Guidance', words=2)"

    def test_repr_format_with_lines(self):
        sec = make_document_section(
            name="Guidance", content="word1 word2", line_start=10, line_end=25
        )
        assert repr(sec) == "DocumentSection(name='Guidance', words=2, lines 10-25)"

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        sec = make_document_section()
        data = sec.to_json()
        assert isinstance(data, dict)
        assert data["name"] == "Guidance"
        assert "content" in data

    def test_from_json_constructs_instance(self):
        data = {"name": "Test", "content": "Some content here."}
        sec = DocumentSection.from_json(data)
        assert isinstance(sec, DocumentSection)
        assert sec.name == "Test"

    def test_json_round_trip(self):
        original = make_document_section()
        restored = DocumentSection.from_json(original.to_json())
        assert restored == original

    def test_json_round_trip_with_line_numbers(self):
        original = make_document_section(line_start=5, line_end=20)
        restored = DocumentSection.from_json(original.to_json())
        assert restored == original
        assert restored.line_start == 5
        assert restored.line_end == 20

    # -- to_markdown --

    def test_to_markdown_format(self):
        sec = make_document_section(name="Guidance", content="Follow these steps.")
        assert sec.to_markdown() == "## Guidance\n\nFollow these steps."

    # -- line_start / line_end --

    def test_line_start_default_none(self):
        sec = make_document_section()
        assert sec.line_start is None

    def test_line_end_default_none(self):
        sec = make_document_section()
        assert sec.line_end is None

    def test_line_start_populated(self):
        sec = make_document_section(line_start=10)
        assert sec.line_start == 10

    def test_line_end_populated(self):
        sec = make_document_section(line_end=30)
        assert sec.line_end == 30

    # -- validate_self / is_valid --

    def test_validate_self_valid_section(self):
        sec = make_document_section()
        issues = sec.validate_self()
        assert issues == []

    def test_validate_self_blank_name(self):
        sec = make_document_section(name="   ")
        issues = sec.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "blank" in issues[0].issue.lower() or "name" in issues[0].issue.lower()

    def test_is_valid_true(self):
        sec = make_document_section()
        assert sec.is_valid is True

    def test_is_valid_false_blank_name(self):
        sec = make_document_section(name="")
        assert sec.is_valid is False

    # -- get_estimated_tokens --

    def test_get_estimated_tokens_positive(self):
        sec = make_document_section()
        tokens = sec.get_estimated_tokens()
        assert isinstance(tokens, int)
        assert tokens > 0

    # -- word_count / line_count --

    def test_word_count(self):
        sec = make_document_section(content="one two three four five")
        assert sec.word_count == 5

    def test_line_count_single_line(self):
        sec = make_document_section(content="single line")
        assert sec.line_count == 1

    def test_line_count_multi_line(self):
        sec = make_document_section(content="line one\nline two\nline three")
        assert sec.line_count == 3

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        sec = make_document_section()
        assert isinstance(sec, WosDomainObject)

    def test_protocol_str(self):
        sec = make_document_section()
        assert isinstance(str(sec), str)

    def test_protocol_repr(self):
        sec = make_document_section()
        assert isinstance(repr(sec), str)

    def test_protocol_to_json(self):
        sec = make_document_section()
        assert isinstance(sec.to_json(), dict)

    def test_protocol_from_json(self):
        data = {"name": "Test", "content": "Some content."}
        sec = DocumentSection.from_json(data)
        assert isinstance(sec, WosDomainObject)

    def test_protocol_validate_self(self):
        sec = make_document_section()
        issues = sec.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        sec = make_document_section()
        assert isinstance(sec.is_valid, bool)


# ══════════════════════════════════════════════════════════════════
# SectionSpec DDD protocol tests
# ══════════════════════════════════════════════════════════════════


class TestSectionSpecProtocol:
    """DDD protocol tests for SectionSpec."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        spec = make_section_spec()
        with pytest.raises(ValidationError):
            spec.name = "Changed"

    def test_hashable(self):
        spec = make_section_spec()
        assert isinstance(hash(spec), int)

    def test_hashable_in_set(self):
        s1 = make_section_spec()
        s2 = make_section_spec()
        assert len({s1, s2}) == 1

    def test_equality_same_values(self):
        s1 = make_section_spec()
        s2 = make_section_spec()
        assert s1 == s2

    def test_equality_different_values(self):
        s1 = make_section_spec(name="Guidance")
        s2 = make_section_spec(name="Context")
        assert s1 != s2

    # -- __str__ and __repr__ --

    def test_str_format(self):
        spec = make_section_spec(name="Guidance", position=1)
        assert str(spec) == "Guidance @1"

    def test_repr_format(self):
        spec = make_section_spec(name="Guidance", position=1)
        assert repr(spec) == "SectionSpec(name='Guidance', position=1)"

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        spec = make_section_spec()
        data = spec.to_json()
        assert isinstance(data, dict)
        assert data["name"] == "Guidance"
        assert data["position"] == 1

    def test_from_json_constructs_instance(self):
        data = {"name": "Context", "position": 2}
        spec = SectionSpec.from_json(data)
        assert isinstance(spec, SectionSpec)
        assert spec.name == "Context"
        assert spec.position == 2

    def test_json_round_trip(self):
        original = make_section_spec()
        restored = SectionSpec.from_json(original.to_json())
        assert restored == original

    # -- validate_self / is_valid --

    def test_validate_self_valid_spec(self):
        spec = make_section_spec()
        issues = spec.validate_self()
        assert issues == []

    def test_validate_self_position_less_than_1(self):
        spec = make_section_spec(position=0)
        issues = spec.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "position" in issues[0].issue.lower() or "less than 1" in issues[0].issue.lower()

    def test_validate_self_blank_name(self):
        spec = make_section_spec(name="   ")
        issues = spec.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "blank" in issues[0].issue.lower() or "name" in issues[0].issue.lower()

    def test_is_valid_true(self):
        spec = make_section_spec()
        assert spec.is_valid is True

    def test_is_valid_false_bad_position(self):
        spec = make_section_spec(position=-1)
        assert spec.is_valid is False

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        spec = make_section_spec()
        assert isinstance(spec, WosDomainObject)

    def test_protocol_str(self):
        spec = make_section_spec()
        assert isinstance(str(spec), str)

    def test_protocol_repr(self):
        spec = make_section_spec()
        assert isinstance(repr(spec), str)

    def test_protocol_to_json(self):
        spec = make_section_spec()
        assert isinstance(spec.to_json(), dict)

    def test_protocol_from_json(self):
        data = {"name": "Test", "position": 1}
        spec = SectionSpec.from_json(data)
        assert isinstance(spec, WosDomainObject)

    def test_protocol_validate_self(self):
        spec = make_section_spec()
        issues = spec.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        spec = make_section_spec()
        assert isinstance(spec.is_valid, bool)


# ══════════════════════════════════════════════════════════════════
# SizeBounds DDD protocol tests
# ══════════════════════════════════════════════════════════════════


class TestSizeBoundsProtocol:
    """DDD protocol tests for SizeBounds."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        sb = make_size_bounds()
        with pytest.raises(ValidationError):
            sb.min_lines = 20

    def test_hashable(self):
        sb = make_size_bounds()
        assert isinstance(hash(sb), int)

    def test_hashable_in_set(self):
        s1 = make_size_bounds()
        s2 = make_size_bounds()
        assert len({s1, s2}) == 1

    def test_equality_same_values(self):
        s1 = make_size_bounds()
        s2 = make_size_bounds()
        assert s1 == s2

    def test_equality_different_values(self):
        s1 = make_size_bounds(min_lines=10)
        s2 = make_size_bounds(min_lines=20)
        assert s1 != s2

    # -- __str__ and __repr__ --

    def test_str_format_with_max(self):
        sb = make_size_bounds(min_lines=10, max_lines=500)
        assert str(sb) == "10-500 lines"

    def test_str_format_without_max(self):
        sb = make_size_bounds(min_lines=10, max_lines=None)
        assert str(sb) == "10+ lines"

    def test_repr_format(self):
        sb = make_size_bounds(min_lines=10, max_lines=500)
        assert repr(sb) == "SizeBounds(min_lines=10, max_lines=500)"

    def test_repr_format_no_max(self):
        sb = make_size_bounds(min_lines=10, max_lines=None)
        assert repr(sb) == "SizeBounds(min_lines=10, max_lines=None)"

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        sb = make_size_bounds()
        data = sb.to_json()
        assert isinstance(data, dict)
        assert data["min_lines"] == 10
        assert data["max_lines"] == 500

    def test_from_json_constructs_instance(self):
        data = {"min_lines": 20, "max_lines": 300}
        sb = SizeBounds.from_json(data)
        assert isinstance(sb, SizeBounds)
        assert sb.min_lines == 20
        assert sb.max_lines == 300

    def test_json_round_trip(self):
        original = make_size_bounds()
        restored = SizeBounds.from_json(original.to_json())
        assert restored == original

    def test_json_round_trip_no_max(self):
        original = make_size_bounds(max_lines=None)
        restored = SizeBounds.from_json(original.to_json())
        assert restored == original

    # -- validate_self / is_valid --

    def test_validate_self_valid(self):
        sb = make_size_bounds()
        issues = sb.validate_self()
        assert issues == []

    def test_validate_self_min_lines_less_than_1(self):
        sb = make_size_bounds(min_lines=0)
        issues = sb.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "min_lines" in issues[0].issue.lower()

    def test_validate_self_max_less_than_min(self):
        sb = make_size_bounds(min_lines=100, max_lines=50)
        issues = sb.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "max_lines" in issues[0].issue.lower()

    def test_is_valid_true(self):
        sb = make_size_bounds()
        assert sb.is_valid is True

    def test_is_valid_false_bad_min(self):
        sb = make_size_bounds(min_lines=-1)
        assert sb.is_valid is False

    def test_is_valid_false_max_less_than_min(self):
        sb = make_size_bounds(min_lines=100, max_lines=10)
        assert sb.is_valid is False

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        sb = make_size_bounds()
        assert isinstance(sb, WosDomainObject)

    def test_protocol_str(self):
        sb = make_size_bounds()
        assert isinstance(str(sb), str)

    def test_protocol_repr(self):
        sb = make_size_bounds()
        assert isinstance(repr(sb), str)

    def test_protocol_to_json(self):
        sb = make_size_bounds()
        assert isinstance(sb.to_json(), dict)

    def test_protocol_from_json(self):
        data = {"min_lines": 5, "max_lines": 100}
        sb = SizeBounds.from_json(data)
        assert isinstance(sb, WosDomainObject)

    def test_protocol_validate_self(self):
        sb = make_size_bounds()
        issues = sb.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        sb = make_size_bounds()
        assert isinstance(sb.is_valid, bool)


# ══════════════════════════════════════════════════════════════════
# VerificationResult DDD protocol tests
# ══════════════════════════════════════════════════════════════════


class TestVerificationResultProtocol:
    """DDD protocol tests for VerificationResult."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        vr = make_verification_result()
        with pytest.raises(ValidationError):
            vr.url = "https://other.com"

    def test_hashable(self):
        vr = make_verification_result()
        assert isinstance(hash(vr), int)

    def test_hashable_in_set(self):
        v1 = make_verification_result()
        v2 = make_verification_result()
        assert len({v1, v2}) == 1

    def test_equality_same_values(self):
        v1 = make_verification_result()
        v2 = make_verification_result()
        assert v1 == v2

    def test_equality_different_values(self):
        v1 = make_verification_result(url="https://a.com")
        v2 = make_verification_result(url="https://b.com")
        assert v1 != v2

    # -- __str__ and __repr__ --

    def test_str_format(self):
        vr = make_verification_result(action="ok", url="https://example.com")
        assert str(vr) == "ok: https://example.com"

    def test_repr_format(self):
        vr = make_verification_result(
            action="ok", url="https://example.com", reason="Title matches"
        )
        assert repr(vr) == (
            "VerificationResult(action='ok', url='https://example.com', "
            "reason='Title matches')"
        )

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        vr = make_verification_result()
        data = vr.to_json()
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com"
        assert data["cited_title"] == "Example"
        assert data["http_status"] == 200
        assert data["page_title"] == "Example Page"
        assert data["title_match"] is True
        assert data["action"] == "ok"
        assert data["reason"] == "Title matches"

    def test_from_json_constructs_instance(self):
        data = {
            "url": "https://example.com",
            "cited_title": "Example",
            "http_status": 200,
            "page_title": "Example Page",
            "title_match": True,
            "action": "ok",
            "reason": "Title matches",
        }
        vr = VerificationResult.from_json(data)
        assert isinstance(vr, VerificationResult)
        assert vr.url == "https://example.com"
        assert vr.action == "ok"

    def test_json_round_trip(self):
        original = make_verification_result()
        restored = VerificationResult.from_json(original.to_json())
        assert restored == original

    # -- validate_self / is_valid --

    def test_validate_self_valid_result(self):
        vr = make_verification_result()
        issues = vr.validate_self()
        assert issues == []

    def test_validate_self_invalid_action(self):
        vr = make_verification_result(action="invalid_action")
        issues = vr.validate_self()
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.WARN
        assert "action" in issues[0].issue.lower() or "invalid" in issues[0].issue.lower()

    def test_is_valid_true(self):
        vr = make_verification_result()
        assert vr.is_valid is True

    def test_is_valid_false_bad_action(self):
        vr = make_verification_result(action="unknown")
        assert vr.is_valid is False

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        vr = make_verification_result()
        assert isinstance(vr, WosDomainObject)

    def test_protocol_str(self):
        vr = make_verification_result()
        assert isinstance(str(vr), str)

    def test_protocol_repr(self):
        vr = make_verification_result()
        assert isinstance(repr(vr), str)

    def test_protocol_to_json(self):
        vr = make_verification_result()
        assert isinstance(vr.to_json(), dict)

    def test_protocol_from_json(self):
        data = {
            "url": "https://example.com",
            "cited_title": "Test",
            "http_status": 200,
            "page_title": "Test Page",
            "title_match": True,
            "action": "ok",
            "reason": "OK",
        }
        vr = VerificationResult.from_json(data)
        assert isinstance(vr, WosDomainObject)

    def test_protocol_validate_self(self):
        vr = make_verification_result()
        issues = vr.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        vr = make_verification_result()
        assert isinstance(vr.is_valid, bool)


# ══════════════════════════════════════════════════════════════════
# ReachabilityResult DDD protocol tests
# ══════════════════════════════════════════════════════════════════


class TestReachabilityResultProtocol:
    """DDD protocol tests for ReachabilityResult."""

    # -- Frozen / immutable --

    def test_frozen_rejects_assignment(self):
        rr = make_reachability_result()
        with pytest.raises(ValidationError):
            rr.url = "https://other.com"

    def test_hashable(self):
        rr = make_reachability_result()
        assert isinstance(hash(rr), int)

    def test_hashable_in_set(self):
        r1 = make_reachability_result()
        r2 = make_reachability_result()
        assert len({r1, r2}) == 1

    def test_equality_same_values(self):
        r1 = make_reachability_result()
        r2 = make_reachability_result()
        assert r1 == r2

    def test_equality_different_values(self):
        r1 = make_reachability_result(url="https://a.com")
        r2 = make_reachability_result(url="https://b.com")
        assert r1 != r2

    # -- __str__ and __repr__ --

    def test_str_reachable(self):
        rr = make_reachability_result(reachable=True, url="https://example.com")
        assert str(rr) == "reachable: https://example.com"

    def test_str_unreachable(self):
        rr = make_reachability_result(reachable=False, url="https://example.com")
        assert str(rr) == "unreachable: https://example.com"

    def test_repr_format(self):
        rr = make_reachability_result(
            url="https://example.com", reachable=True, reason="OK"
        )
        assert repr(rr) == (
            "ReachabilityResult(reachable=True, url='https://example.com', "
            "reason='OK')"
        )

    # -- to_json / from_json / round-trip --

    def test_to_json_returns_dict(self):
        rr = make_reachability_result()
        data = rr.to_json()
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com"
        assert data["http_status"] == 200
        assert data["reachable"] is True
        assert data["reason"] == "OK"
        assert data["final_url"] == "https://example.com"

    def test_from_json_constructs_instance(self):
        data = {
            "url": "https://example.com",
            "http_status": 200,
            "reachable": True,
            "reason": "OK",
            "final_url": "https://example.com",
        }
        rr = ReachabilityResult.from_json(data)
        assert isinstance(rr, ReachabilityResult)
        assert rr.url == "https://example.com"
        assert rr.reachable is True

    def test_json_round_trip(self):
        original = make_reachability_result()
        restored = ReachabilityResult.from_json(original.to_json())
        assert restored == original

    # -- validate_self / is_valid --

    def test_validate_self_valid_result(self):
        rr = make_reachability_result()
        issues = rr.validate_self()
        assert issues == []

    def test_is_valid_true(self):
        rr = make_reachability_result()
        assert rr.is_valid is True

    # -- WosDomainObject protocol conformance --

    def test_protocol_conformance(self):
        rr = make_reachability_result()
        assert isinstance(rr, WosDomainObject)

    def test_protocol_str(self):
        rr = make_reachability_result()
        assert isinstance(str(rr), str)

    def test_protocol_repr(self):
        rr = make_reachability_result()
        assert isinstance(repr(rr), str)

    def test_protocol_to_json(self):
        rr = make_reachability_result()
        assert isinstance(rr.to_json(), dict)

    def test_protocol_from_json(self):
        data = {
            "url": "https://example.com",
            "http_status": 200,
            "reachable": True,
            "reason": "OK",
            "final_url": "https://example.com",
        }
        rr = ReachabilityResult.from_json(data)
        assert isinstance(rr, WosDomainObject)

    def test_protocol_validate_self(self):
        rr = make_reachability_result()
        issues = rr.validate_self()
        assert isinstance(issues, list)

    def test_protocol_is_valid(self):
        rr = make_reachability_result()
        assert isinstance(rr.is_valid, bool)


# ══════════════════════════════════════════════════════════════════
# Line number tracking tests (parse_document integration)
# ══════════════════════════════════════════════════════════════════


from wos.models.parsing import parse_document


class TestLineNumberTracking:
    def test_frontmatter_line_end(self):
        md = (
            "---\n"                  # line 1
            "document_type: plan\n"  # line 2
            'description: "Implementation plan for a four-type document system"\n'
            "last_updated: 2026-02-17\n"
            "---\n"                  # line 5
            "\n"
            "# My Plan\n"           # line 7
            "\n"
            "## Objective\n"        # line 9
            "\n"
            "Goal here.\n"
            "\n"
            "## Context\n"          # line 13
            "\n"
            "Background.\n"
            "\n"
            "## Steps\n"            # line 17
            "\n"
            "1. Do stuff.\n"
            "\n"
            "## Verification\n"     # line 21
            "\n"
            "- It works.\n"
        )
        doc = parse_document("artifacts/plans/2026-02-17-plan.md", md)
        assert doc.frontmatter_line_end == 5
        assert doc.title_line == 7

    def test_section_line_numbers(self):
        md = (
            "---\n"
            "document_type: plan\n"
            'description: "Implementation plan for a four-type document system"\n'
            "last_updated: 2026-02-17\n"
            "---\n"
            "\n"
            "# My Plan\n"
            "\n"
            "## Objective\n"        # line 9
            "\n"
            "Goal here.\n"
            "\n"
            "## Context\n"          # line 13
            "\n"
            "Background.\n"
            "\n"
            "## Steps\n"            # line 17
            "\n"
            "1. Do stuff.\n"
            "\n"
            "## Verification\n"     # line 21
            "\n"
            "- It works.\n"
        )
        doc = parse_document("artifacts/plans/2026-02-17-plan.md", md)
        objective = doc.get_section("Objective")
        assert objective is not None
        assert objective.line_start == 9

        verification = doc.get_section("Verification")
        assert verification is not None
        assert verification.line_start == 21

    def test_section_line_numbers_topic(self):
        md = (
            "---\n"
            "document_type: topic\n"
            "description: 'A topic about testing'\n"
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            "sources:\n"
            '  - url: "https://example.com"\n'
            '    title: "Example"\n'
            "---\n"                      # line 9
            "\n"
            "# Testing Topic\n"         # line 11
            "\n"
            "## Guidance\n"             # line 13
            "\n"
            "Follow these steps.\n"
            "\n"
            "## Context\n"             # line 17
            "\n"
            "This is context.\n"
            "\n"
            "## In Practice\n"         # line 21
            "\n"
            "Do this.\n"
            "\n"
            "## Pitfalls\n"            # line 25
            "\n"
            "Avoid that.\n"
            "\n"
            "## Go Deeper\n"           # line 29
            "\n"
            "Learn more.\n"
        )
        doc = parse_document("context/testing/basics.md", md)
        assert doc.frontmatter_line_end == 9
        assert doc.title_line == 11

        guidance = doc.get_section("Guidance")
        assert guidance is not None
        assert guidance.line_start == 13

        go_deeper = doc.get_section("Go Deeper")
        assert go_deeper is not None
        assert go_deeper.line_start == 29
