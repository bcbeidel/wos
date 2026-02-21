"""Tests for document parsing and line number tracking.

Tests the _split_markdown parser and parse_document entry point,
focusing on line number accuracy for frontmatter, title, and sections.
"""
from __future__ import annotations

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
