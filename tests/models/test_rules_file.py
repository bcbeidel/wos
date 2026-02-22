"""Tests for RulesFile value object."""
from __future__ import annotations

import pytest

from wos.models.rules_file import RulesFile


class TestRulesFile:
    def test_render_produces_content(self):
        rf = RulesFile.render()
        assert isinstance(rf, RulesFile)
        assert "Document Types" in rf.content

    def test_to_markdown(self):
        rf = RulesFile.render()
        assert isinstance(rf.to_markdown(), str)
        assert rf.to_markdown() == rf.content

    def test_validate_self_valid(self):
        rf = RulesFile.render()
        assert rf.validate_self() == []

    def test_is_valid(self):
        rf = RulesFile.render()
        assert rf.is_valid is True

    def test_str(self):
        rf = RulesFile.render()
        assert "RulesFile" in str(rf) or "lines" in str(rf).lower()

    def test_repr(self):
        rf = RulesFile.render()
        assert "RulesFile" in repr(rf)

    def test_empty_content_not_valid(self):
        rf = RulesFile(content="")
        assert rf.is_valid is False

    def test_frozen(self):
        rf = RulesFile.render()
        with pytest.raises(Exception):
            rf.content = "changed"

    def test_to_json_round_trip(self):
        rf = RulesFile.render()
        data = rf.to_json()
        restored = RulesFile.from_json(data)
        assert restored.content == rf.content

    def test_builder(self):
        from tests.builders import make_rules_file
        rf = make_rules_file()
        assert isinstance(rf, RulesFile)
        assert rf.is_valid is True
