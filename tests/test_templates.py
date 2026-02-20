"""Tests for wos.templates — document template rendering.

All templates must produce output that passes parse_document() validation.
"""

from __future__ import annotations

from wos.document_types import (
    SECTIONS,
    DocumentType,
    Source,
    parse_document,
)
from wos.templates import (
    render_overview,
    render_plan,
    render_research,
    render_topic,
)

# ── Polymorphic dispatch ─────────────────────────────────────────


class TestFromTemplate:
    def test_all_subclasses_have_from_template(self) -> None:
        from wos.models.documents import (
            NoteDocument,
            OverviewDocument,
            PlanDocument,
            ResearchDocument,
            TopicDocument,
        )

        for cls in [
            TopicDocument, OverviewDocument, ResearchDocument,
            PlanDocument, NoteDocument,
        ]:
            assert hasattr(cls, "from_template")
            assert callable(cls.from_template)


# ── render_topic ─────────────────────────────────────────────────


class TestRenderTopic:
    def test_round_trip(self) -> None:
        sources = [
            Source(url="https://docs.python.org", title="Python Docs"),
            Source(url="https://realpython.com", title="Real Python"),
        ]
        md = render_topic(
            "Error Handling",
            "When and how to use exceptions in Python",
            sources,
        )
        doc = parse_document("context/python/error-handling.md", md)
        assert doc.frontmatter.document_type == "topic"
        assert doc.title == "Error Handling"

    def test_has_all_required_sections(self) -> None:
        sources = [
            Source(url="https://example.com", title="Example"),
        ]
        md = render_topic("Test", "A test topic for validation", sources)
        doc = parse_document("context/test/test.md", md)
        required = {s.name for s in SECTIONS[DocumentType.TOPIC]}
        assert required.issubset(set(doc.section_names))

    def test_custom_section_content(self) -> None:
        sources = [
            Source(url="https://example.com", title="Example"),
        ]
        md = render_topic(
            "Test",
            "A test topic for validation",
            sources,
            section_content={"Guidance": "Custom guidance content."},
        )
        doc = parse_document("context/test/test.md", md)
        assert "Custom guidance content." in doc.get_section_content("Guidance")


# ── render_overview ──────────────────────────────────────────────


class TestRenderOverview:
    def test_round_trip(self) -> None:
        md = render_overview(
            "Python",
            "Core Python programming concepts and best practices",
        )
        doc = parse_document("context/python/_overview.md", md)
        assert doc.frontmatter.document_type == "overview"
        assert doc.title == "Python"

    def test_has_all_required_sections(self) -> None:
        md = render_overview(
            "Python",
            "Core Python programming concepts and best practices",
        )
        doc = parse_document("context/python/_overview.md", md)
        required = {s.name for s in SECTIONS[DocumentType.OVERVIEW]}
        assert required.issubset(set(doc.section_names))

    def test_topics_list(self) -> None:
        md = render_overview(
            "Python",
            "Core Python programming concepts and best practices",
            topics=["Error Handling", "Testing"],
        )
        doc = parse_document("context/python/_overview.md", md)
        assert "Error Handling" in doc.get_section_content("Topics")
        assert "Testing" in doc.get_section_content("Topics")

    def test_what_this_covers_auto_generated(self) -> None:
        md = render_overview(
            "Python",
            "Core Python programming concepts and best practices",
        )
        doc = parse_document("context/python/_overview.md", md)
        # Auto-generated What This Covers should have enough words
        words = len(doc.get_section_content("What This Covers").split())
        assert words >= 30


# ── render_research ──────────────────────────────────────────────


class TestRenderResearch:
    def test_round_trip(self) -> None:
        sources = [
            Source(url="https://example.com", title="Example"),
        ]
        md = render_research(
            "Error Handling Patterns",
            "Investigation of error handling best practices",
            sources,
        )
        path = "artifacts/research/2026-02-17-error-handling.md"
        doc = parse_document(path, md)
        assert doc.frontmatter.document_type == "research"

    def test_has_all_required_sections(self) -> None:
        sources = [
            Source(url="https://example.com", title="Example"),
        ]
        md = render_research(
            "Test",
            "A test research document for validation",
            sources,
        )
        path = "artifacts/research/2026-02-17-test.md"
        doc = parse_document(path, md)
        required = {s.name for s in SECTIONS[DocumentType.RESEARCH]}
        assert required.issubset(set(doc.section_names))

    def test_no_last_validated(self) -> None:
        sources = [
            Source(url="https://example.com", title="Example"),
        ]
        md = render_research(
            "Test",
            "A test research document for validation",
            sources,
        )
        assert "last_validated" not in md


# ── render_plan ──────────────────────────────────────────────────


class TestRenderPlan:
    def test_round_trip(self) -> None:
        md = render_plan(
            "Improve Error Handling",
            "Plan to improve error handling across the codebase",
        )
        path = "artifacts/plans/2026-02-17-improve-errors.md"
        doc = parse_document(path, md)
        assert doc.frontmatter.document_type == "plan"

    def test_has_all_required_sections(self) -> None:
        md = render_plan(
            "Test",
            "A test plan document for validation purposes",
        )
        path = "artifacts/plans/2026-02-17-test.md"
        doc = parse_document(path, md)
        required = {s.name for s in SECTIONS[DocumentType.PLAN]}
        assert required.issubset(set(doc.section_names))

    def test_no_last_validated(self) -> None:
        md = render_plan(
            "Test",
            "A test plan document for validation purposes",
        )
        assert "last_validated" not in md


# ── Edge cases ───────────────────────────────────────────────────


class TestEdgeCases:
    def test_description_with_quotes(self) -> None:
        sources = [
            Source(url="https://example.com", title="Example"),
        ]
        md = render_topic(
            "Test",
            'Description with "quotes" inside',
            sources,
        )
        doc = parse_document("context/test/test.md", md)
        assert "quotes" in doc.frontmatter.description

    def test_source_title_with_quotes(self) -> None:
        sources = [
            Source(
                url="https://example.com",
                title='The "Great" Guide',
            ),
        ]
        md = render_topic(
            "Test",
            "A test topic for source title escaping",
            sources,
        )
        doc = parse_document("context/test/test.md", md)
        assert len(doc.frontmatter.sources) == 1


class TestRenderNote:
    def test_round_trip(self):
        from wos.templates import render_note

        md = render_note("My Note", "Personal notes on a specific topic area")
        doc = parse_document("notes/test.md", md)
        assert doc.document_type == DocumentType.NOTE
        assert doc.frontmatter.description == (
            "Personal notes on a specific topic area"
        )
        assert doc.title == "My Note"

    def test_no_sections(self):
        from wos.templates import render_note

        md = render_note("My Note", "Personal notes on a specific topic area")
        doc = parse_document("notes/test.md", md)
        # Note: the template has a placeholder comment, but no H2 sections
        # So sections dict should be empty
        assert doc.sections == []

    def test_note_has_from_template(self):
        from wos.models.documents import NoteDocument

        assert hasattr(NoteDocument, "from_template")
        assert callable(NoteDocument.from_template)
