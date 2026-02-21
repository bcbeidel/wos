"""DDD protocol tests for DocumentSection.

Covers: frozen/immutable, hashable, equality, __str__, __repr__,
to_json, from_json, json round-trip, to_markdown, line numbers,
validate_self, is_valid, get_estimated_tokens, word_count, line_count,
and WosDomainObject protocol conformance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.builders import make_document_section
from wos.models.enums import IssueSeverity
from wos.models.protocol import WosDomainObject
from wos.models.section import DocumentSection


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
