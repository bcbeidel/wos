"""DDD protocol tests for CitedSource.

Covers: frozen/immutable, hashable, equality, __str__, __repr__,
to_json, from_json, json round-trip, to_markdown, from_markdown_link,
markdown round-trip, to_yaml_entry, validate_self, is_valid,
builder usage, and WosDomainObject protocol conformance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.builders import make_cited_source
from wos.models.cited_source import CitedSource
from wos.models.enums import IssueSeverity
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
