"""DDD protocol tests for SectionSpec and SizeBounds.

Covers: frozen/immutable, hashable, equality, __str__, __repr__,
to_json, from_json, json round-trip, validate_self, is_valid,
and WosDomainObject protocol conformance.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.builders import make_section_spec, make_size_bounds
from wos.models.enums import IssueSeverity
from wos.models.frontmatter import SectionSpec, SizeBounds
from wos.models.protocol import WosDomainObject


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
