"""DDD protocol tests for BaseDocument.

Covers: __str__, __repr__, __len__, __iter__, __contains__,
area_name property, from_markdown, to_json/from_json, to_markdown,
validate_self, is_valid, and builder.
"""
from __future__ import annotations

from wos.models.base_document import BaseDocument
from wos.models.parsing import parse_document
from wos.models.validation_issue import ValidationIssue


TOPIC_MD = (
    "---\n"
    "document_type: topic\n"
    'description: "Test topic document"\n'
    "last_updated: 2026-02-17\n"
    "last_validated: 2026-02-17\n"
    "sources:\n"
    '  - url: "https://example.com"\n'
    '    title: "Example"\n'
    "---\n"
    "\n"
    "# Test Topic\n"
    "\n"
    "## Guidance\n"
    "\n"
    "Follow these steps.\n"
    "\n"
    "## Context\n"
    "\n"
    "Background info.\n"
    "\n"
    "## In Practice\n"
    "\n"
    "Do this.\n"
    "\n"
    "## Pitfalls\n"
    "\n"
    "Avoid that.\n"
    "\n"
    "## Go Deeper\n"
    "\n"
    "- [Example Resource](https://example.com/resource)\n"
)


class TestBaseDocumentProtocol:
    """DDD protocol tests for BaseDocument."""

    def _make_topic_doc(self, path: str = "context/testing/example.md") -> BaseDocument:
        return parse_document(path, TOPIC_MD)

    # -- __str__ --

    def test_str_representation(self):
        doc = self._make_topic_doc()
        assert str(doc) == "Test Topic (topic)"

    # -- __repr__ --

    def test_repr_representation(self):
        doc = self._make_topic_doc()
        # parse_document returns the appropriate subclass (TopicDocument)
        expected = f"{type(doc).__name__}(path='context/testing/example.md', type='topic')"
        assert repr(doc) == expected

    # -- __len__ --

    def test_len_returns_section_count(self):
        doc = self._make_topic_doc()
        assert len(doc) == 5

    # -- __iter__ --

    def test_iter_yields_sections(self):
        doc = self._make_topic_doc()
        sections = list(doc)
        assert len(sections) == 5
        assert sections[0].name == "Guidance"
        assert sections[-1].name == "Go Deeper"

    # -- __contains__ --

    def test_contains_section_name(self):
        doc = self._make_topic_doc()
        assert "Guidance" in doc
        assert "Nonexistent" not in doc

    def test_contains_section_object(self):
        doc = self._make_topic_doc()
        assert doc.sections[0] in doc

    # -- area_name --

    def test_area_name_from_context_path(self):
        doc = self._make_topic_doc("context/testing/example.md")
        assert doc.area_name == "testing"

    def test_area_name_none_for_artifact(self):
        plan_md = (
            "---\n"
            "document_type: plan\n"
            'description: "A plan for testing"\n'
            "last_updated: 2026-02-17\n"
            "---\n"
            "\n"
            "# Test Plan\n"
            "\n"
            "## Objective\n"
            "\n"
            "Goal here.\n"
            "\n"
            "## Context\n"
            "\n"
            "Background.\n"
            "\n"
            "## Steps\n"
            "\n"
            "1. Do stuff.\n"
            "\n"
            "## Verification\n"
            "\n"
            "- It works.\n"
        )
        doc = parse_document("artifacts/plans/2026-01-01-test.md", plan_md)
        assert doc.area_name is None

    # -- from_markdown --

    def test_from_markdown_round_trip(self):
        path = "context/testing/example.md"
        doc = BaseDocument.from_markdown(path, TOPIC_MD)
        assert isinstance(doc, BaseDocument)
        assert doc.title == "Test Topic"
        assert doc.path == path

    # -- to_json / from_json --

    def test_to_json_round_trip(self):
        doc = self._make_topic_doc()
        data = doc.to_json()
        assert isinstance(data, dict)
        assert data["path"] == "context/testing/example.md"
        assert data["document_type"] == "topic"
        assert data["title"] == "Test Topic"
        assert "sections" in data
        assert "frontmatter" in data
        assert "raw_content" in data

        restored = BaseDocument.from_json(data)
        assert isinstance(restored, BaseDocument)
        assert restored.title == doc.title
        assert restored.path == doc.path
        assert len(restored.sections) == len(doc.sections)

    # -- to_markdown --

    def test_to_markdown_produces_valid_document(self):
        doc = self._make_topic_doc()
        md = doc.to_markdown()
        assert isinstance(md, str)
        assert md.startswith("---\n")
        assert "# Test Topic" in md
        assert "## Guidance" in md

        # Round-trip: the rendered markdown should be parseable
        restored = parse_document("context/testing/example.md", md)
        assert restored.title == doc.title
        assert len(restored.sections) == len(doc.sections)
        for orig, rest in zip(doc.sections, restored.sections):
            assert orig.name == rest.name

    # -- validate_self --

    def test_validate_self_returns_issues(self):
        doc = self._make_topic_doc()
        issues = doc.validate_self()
        assert isinstance(issues, list)

    # -- is_valid --

    def test_is_valid_property(self):
        doc = self._make_topic_doc()
        assert isinstance(doc.is_valid, bool)
        # A well-formed topic doc should be valid
        assert doc.is_valid is True

    # -- validate_content --

    def test_validate_content_returns_validation_issues(self):
        """validate_content() returns ValidationIssue objects, not raw dicts."""
        short_desc_md = (
            "---\n"
            "document_type: topic\n"
            'description: "Short desc."\n'
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            "sources:\n"
            '  - url: "https://example.com"\n'
            '    title: "Example"\n'
            "---\n"
            "\n"
            "# Short Topic\n"
            "\n"
            "## Guidance\n\nContent.\n"
            "\n"
            "## Context\n\nContent.\n"
            "\n"
            "## In Practice\n\n- Do this.\n"
            "\n"
            "## Pitfalls\n\nAvoid that.\n"
            "\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        doc = parse_document("context/testing/example.md", short_desc_md)
        results = doc.validate_content()
        # "Short desc." is < 20 chars, should trigger description quality check
        # Filter to ValidationIssue objects (subclass may still add legacy dicts)
        issues = [r for r in results if isinstance(r, ValidationIssue)]
        assert len(issues) > 0
        for issue in issues:
            assert isinstance(issue, ValidationIssue)
            assert issue.requires_llm is True

    # -- builder --

    def test_builder(self):
        from tests.builders import make_document

        doc = make_document()
        assert isinstance(doc, BaseDocument)
