"""Tests for OverviewDocument validate_content()."""
from __future__ import annotations

from wos.models.core import ValidationIssue
from wos.models.parsing import parse_document


def _make_overview(what_this_covers="This area covers a wide range of topics " * 7):
    md = (
        "---\n"
        "document_type: overview\n"
        'description: "Test overview with enough words"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Test Overview\n"
        "\n"
        f"## What This Covers\n\n{what_this_covers}\n"
        "\n"
        "## Topics\n\n- Topic A\n"
        "\n"
        "## Key Sources\n\n- [Source](https://example.com)\n"
    )
    return parse_document("context/testing/_overview.md", md)


class TestOverviewValidateContent:
    def test_short_coverage_flags_review(self):
        doc = _make_overview(what_this_covers="Brief.")
        issues = doc.validate_content()
        coverage = [i for i in issues if i.section == "What This Covers"]
        assert len(coverage) > 0
        assert all(isinstance(i, ValidationIssue) for i in coverage)
        assert all(i.requires_llm for i in coverage)

    def test_adequate_coverage_no_issue(self):
        doc = _make_overview()
        issues = doc.validate_content()
        coverage = [i for i in issues if i.section == "What This Covers"]
        assert len(coverage) == 0
