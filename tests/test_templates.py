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
    TEMPLATES,
    render_overview,
    render_plan,
    render_research,
    render_topic,
)

# ── Dispatch table ───────────────────────────────────────────────


class TestDispatchTable:
    def test_all_types_have_templates(self) -> None:
        for dt in DocumentType:
            assert dt in TEMPLATES, f"{dt} missing from TEMPLATES"

    def test_templates_are_callable(self) -> None:
        for dt, fn in TEMPLATES.items():
            assert callable(fn), f"TEMPLATES[{dt}] is not callable"


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
        assert required.issubset(set(doc.sections.keys()))

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
        assert "Custom guidance content." in doc.sections["Guidance"]


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
        assert required.issubset(set(doc.sections.keys()))

    def test_topics_list(self) -> None:
        md = render_overview(
            "Python",
            "Core Python programming concepts and best practices",
            topics=["Error Handling", "Testing"],
        )
        doc = parse_document("context/python/_overview.md", md)
        assert "Error Handling" in doc.sections["Topics"]
        assert "Testing" in doc.sections["Topics"]

    def test_what_this_covers_auto_generated(self) -> None:
        md = render_overview(
            "Python",
            "Core Python programming concepts and best practices",
        )
        doc = parse_document("context/python/_overview.md", md)
        # Auto-generated What This Covers should have enough words
        words = len(doc.sections["What This Covers"].split())
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
        assert required.issubset(set(doc.sections.keys()))

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
        assert doc.frontmatter.status.value == "draft"

    def test_custom_status(self) -> None:
        md = render_plan(
            "Active Plan",
            "A plan that is already in progress",
            status="active",
        )
        path = "artifacts/plans/2026-02-17-active.md"
        doc = parse_document(path, md)
        assert doc.frontmatter.status.value == "active"

    def test_has_all_required_sections(self) -> None:
        md = render_plan(
            "Test",
            "A test plan document for validation purposes",
        )
        path = "artifacts/plans/2026-02-17-test.md"
        doc = parse_document(path, md)
        required = {s.name for s in SECTIONS[DocumentType.PLAN]}
        assert required.issubset(set(doc.sections.keys()))

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
