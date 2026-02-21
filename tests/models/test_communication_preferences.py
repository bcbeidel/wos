"""Tests for CommunicationPreferences value object."""
from __future__ import annotations

import pytest

from wos.models.communication_preferences import CommunicationPreferences
from wos.models.validation_issue import ValidationIssue


class TestCommunicationPreferences:
    def test_construction(self):
        prefs = CommunicationPreferences(dimensions={"directness": "blunt"})
        assert prefs.dimensions["directness"] == "blunt"

    def test_frozen(self):
        prefs = CommunicationPreferences(dimensions={"directness": "blunt"})
        with pytest.raises(Exception):
            prefs.dimensions = {"tone": "formal"}

    def test_render_section(self):
        prefs = CommunicationPreferences(
            dimensions={"directness": "blunt", "tone": "casual"}
        )
        rendered = prefs.render_section()
        assert "Directness" in rendered
        assert "Tone" in rendered
        assert "Be direct" in rendered

    def test_render_section_all_dimensions(self):
        prefs = CommunicationPreferences(
            dimensions={
                "directness": "balanced",
                "verbosity": "moderate",
                "depth": "context-when-useful",
                "expertise": "intermediate",
                "tone": "neutral",
            }
        )
        rendered = prefs.render_section()
        assert rendered.count("- **") == 5

    def test_validate_self_valid(self):
        prefs = CommunicationPreferences(dimensions={"directness": "blunt"})
        assert prefs.validate_self() == []

    def test_validate_self_invalid_dimension(self):
        prefs = CommunicationPreferences(dimensions={"unknown": "value"})
        issues = prefs.validate_self()
        assert len(issues) > 0
        assert any("unknown" in i.issue.lower() for i in issues)

    def test_validate_self_invalid_level(self):
        prefs = CommunicationPreferences(dimensions={"directness": "invalid"})
        issues = prefs.validate_self()
        assert len(issues) > 0

    def test_is_valid(self):
        prefs = CommunicationPreferences(dimensions={"tone": "formal"})
        assert prefs.is_valid is True

    def test_is_valid_false(self):
        prefs = CommunicationPreferences(dimensions={"bad": "value"})
        assert prefs.is_valid is False

    def test_str(self):
        prefs = CommunicationPreferences(dimensions={"directness": "blunt"})
        assert "1" in str(prefs) or "directness" in str(prefs).lower()

    def test_repr(self):
        prefs = CommunicationPreferences(dimensions={"directness": "blunt"})
        assert "CommunicationPreferences" in repr(prefs)

    def test_to_json_round_trip(self):
        prefs = CommunicationPreferences(
            dimensions={"directness": "blunt", "tone": "casual"}
        )
        data = prefs.to_json()
        restored = CommunicationPreferences.from_json(data)
        assert restored.dimensions == prefs.dimensions

    def test_builder(self):
        from tests.builders import make_communication_preferences
        prefs = make_communication_preferences()
        assert isinstance(prefs, CommunicationPreferences)
        assert prefs.is_valid is True
