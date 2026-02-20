"""Tests for wos.document_types — the foundation module.

All tests use inline markdown strings (no fixture files).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from wos.document_types import (
    ARTIFACT_TYPES,
    CONTEXT_TYPES,
    DATE_PREFIX_TYPES,
    DIRECTORY_PATTERNS,
    FRESHNESS_TRACKED_TYPES,
    SECTIONS,
    SIZE_BOUNDS,
    SOURCE_GROUNDED_TYPES,
    DocumentType,
    PlanStatus,
    parse_document,
)

# Types that are deliberately excluded from DIRECTORY_PATTERNS
_TYPES_WITHOUT_DIRECTORY_PATTERN = {DocumentType.NOTE}

# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(
    *,
    description="Core principles for the first 10-15 moves of a chess game",
    last_updated="2026-02-17",
    last_validated="2026-02-17",
    extra_fm="",
) -> str:
    return (
        "---\n"
        "document_type: topic\n"
        f'description: "{description}"\n'
        f"last_updated: {last_updated}\n"
        f"last_validated: {last_validated}\n"
        "sources:\n"
        '  - url: https://example.com/chess\n'
        '    title: "Chess Openings"\n'
        f"{extra_fm}"
        "---\n"
        "\n"
        "# Opening Principles\n"
        "\n"
        "## Guidance\n"
        "\n"
        "Use guidelines.\n"
        "\n"
        "## Context\n"
        "\n"
        "Why it matters.\n"
        "\n"
        "## In Practice\n"
        "\n"
        "Examples here.\n"
        "\n"
        "## Pitfalls\n"
        "\n"
        "Avoid these.\n"
        "\n"
        "## Go Deeper\n"
        "\n"
        "More reading.\n"
    )


def _overview_md(
    *,
    description=(
        "Chess strategy covers opening principles"
        " and middlegame tactics for competitive play"
    ),
    last_updated="2026-02-17",
    last_validated="2026-02-17",
    extra_fm="",
) -> str:
    return (
        "---\n"
        "document_type: overview\n"
        f'description: "{description}"\n'
        f"last_updated: {last_updated}\n"
        f"last_validated: {last_validated}\n"
        f"{extra_fm}"
        "---\n"
        "\n"
        "# Chess Strategy\n"
        "\n"
        "## What This Covers\n"
        "\n"
        "This area covers chess strategy including opening principles,\n"
        "middlegame tactics, and endgame techniques for competitive play.\n"
        "Understanding these fundamentals is essential for improvement.\n"
        "\n"
        "## Topics\n"
        "\n"
        "| Topic | Description |\n"
        "|-------|-------------|\n"
        "| [Opening Principles](opening-principles.md) | Core opening moves |\n"
        "\n"
        "## Key Sources\n"
        "\n"
        "- [Chess.com](https://chess.com)\n"
    )


def _research_md(
    *,
    description=(
        "Investigation of document type systems"
        " across DITA, Diataxis, and Zettelkasten"
    ),
    last_updated="2026-02-17",
    status="",
    extra_fm="",
) -> str:
    status_line = f"status: {status}\n" if status else ""
    return (
        "---\n"
        "document_type: research\n"
        f'description: "{description}"\n'
        f"last_updated: {last_updated}\n"
        "sources:\n"
        '  - url: https://diataxis.fr/\n'
        '    title: "Diataxis Framework"\n'
        f"{status_line}"
        f"{extra_fm}"
        "---\n"
        "\n"
        "# Document Type Systems Deep Dive\n"
        "\n"
        "## Question\n"
        "\n"
        "What document type systems exist and how do they compare?\n"
        "\n"
        "## Findings\n"
        "\n"
        "Several systems were analyzed including DITA and Diataxis.\n"
        "\n"
        "## Implications\n"
        "\n"
        "The four-type system best fits our needs.\n"
        "\n"
        "## Sources\n"
        "\n"
        "- Diataxis Framework: https://diataxis.fr/\n"
    )


def _plan_md(
    *,
    description="Implementation plan for a four-type document system with validators",
    last_updated="2026-02-17",
    status="draft",
    extra_fm="",
) -> str:
    return (
        "---\n"
        "document_type: plan\n"
        f'description: "{description}"\n'
        f"last_updated: {last_updated}\n"
        f"status: {status}\n"
        f"{extra_fm}"
        "---\n"
        "\n"
        "# Implement Document Types\n"
        "\n"
        "## Objective\n"
        "\n"
        "A working document type system exists.\n"
        "\n"
        "## Context\n"
        "\n"
        "Based on prior research into document type systems.\n"
        "\n"
        "## Steps\n"
        "\n"
        "1. Create models\n"
        "2. Add validators\n"
        "\n"
        "## Verification\n"
        "\n"
        "- Tests pass\n"
        "- Import succeeds\n"
    )


def _note_md(
    *,
    description="Personal notes on effective meeting facilitation techniques",
    extra_fm="",
) -> str:
    return (
        "---\n"
        "document_type: note\n"
        f'description: "{description}"\n'
        f"{extra_fm}"
        "---\n"
        "\n"
        "# Meeting Facilitation\n"
        "\n"
        "Some content here.\n"
    )


# ── Valid documents parse correctly ──────────────────────────────


class TestValidDocuments:
    def test_topic_parses(self):
        doc = parse_document("context/chess/opening-principles.md", _topic_md())
        assert doc.document_type == DocumentType.TOPIC
        assert doc.title == "Opening Principles"
        assert doc.has_section("Guidance")
        assert doc.frontmatter.description.startswith("Core principles")

    def test_overview_parses(self):
        doc = parse_document("context/chess/_overview.md", _overview_md())
        assert doc.document_type == DocumentType.OVERVIEW
        assert doc.title == "Chess Strategy"
        assert doc.has_section("What This Covers")

    def test_research_parses(self):
        doc = parse_document(
            "artifacts/research/2026-02-17-doc-types.md", _research_md()
        )
        assert doc.document_type == DocumentType.RESEARCH
        assert doc.has_section("Question")

    def test_plan_parses(self):
        doc = parse_document(
            "artifacts/plans/2026-02-17-doc-types.md", _plan_md()
        )
        assert doc.document_type == DocumentType.PLAN
        assert doc.frontmatter.status == PlanStatus.DRAFT

    def test_research_without_last_validated(self):
        """Research documents do not require last_validated."""
        doc = parse_document(
            "artifacts/research/2026-02-17-doc-types.md", _research_md()
        )
        assert doc.document_type == DocumentType.RESEARCH
        assert not hasattr(doc.frontmatter, "last_validated")

    def test_research_with_optional_status(self):
        """Research documents can have an optional status."""
        doc = parse_document(
            "artifacts/research/2026-02-17-doc-types.md",
            _research_md(status="complete"),
        )
        assert doc.frontmatter.status == PlanStatus.COMPLETE

    def test_research_without_status(self):
        """Research documents work without status."""
        doc = parse_document(
            "artifacts/research/2026-02-17-doc-types.md",
            _research_md(),
        )
        assert doc.frontmatter.status is None

    def test_plan_all_statuses(self):
        """All PlanStatus values are accepted."""
        for status in PlanStatus:
            doc = parse_document(
                "artifacts/plans/2026-02-17-doc-types.md",
                _plan_md(status=status.value),
            )
            assert doc.frontmatter.status == status


# ── Discriminated union routes correctly ─────────────────────────


class TestDiscriminatedUnion:
    def test_topic_routes_to_topic_frontmatter(self):
        doc = parse_document("context/chess/opening.md", _topic_md())
        assert type(doc.frontmatter).__name__ == "TopicFrontmatter"

    def test_overview_routes_to_overview_frontmatter(self):
        doc = parse_document("context/chess/_overview.md", _overview_md())
        assert type(doc.frontmatter).__name__ == "OverviewFrontmatter"

    def test_research_routes_to_research_frontmatter(self):
        doc = parse_document(
            "artifacts/research/2026-02-17-doc.md", _research_md()
        )
        assert type(doc.frontmatter).__name__ == "ResearchFrontmatter"

    def test_plan_routes_to_plan_frontmatter(self):
        doc = parse_document(
            "artifacts/plans/2026-02-17-doc.md", _plan_md()
        )
        assert type(doc.frontmatter).__name__ == "PlanFrontmatter"

    def test_unknown_document_type_raises(self):
        md = (
            "---\n"
            "document_type: unknown\n"
            'description: "This type does not exist in the system"\n'
            "last_updated: 2026-02-17\n"
            "---\n"
            "\n"
            "# Unknown Doc\n"
        )
        with pytest.raises(ValidationError, match="document_type"):
            parse_document("context/chess/unknown.md", md)


# ── Missing required fields ──────────────────────────────────────


class TestMissingFields:
    def test_topic_missing_sources(self):
        md = (
            "---\n"
            "document_type: topic\n"
            'description: "Core principles for the first 10-15 moves of a game"\n'
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            "---\n"
            "\n"
            "# Opening Principles\n"
            "\n"
            "## Guidance\n"
            "\n"
            "Content here.\n"
        )
        with pytest.raises(ValidationError, match="sources"):
            parse_document("context/chess/opening.md", md)

    def test_topic_missing_last_validated(self):
        md = (
            "---\n"
            "document_type: topic\n"
            'description: "Core principles for the first 10-15 moves of a game"\n'
            "last_updated: 2026-02-17\n"
            "sources:\n"
            "  - url: https://example.com\n"
            '    title: "Example"\n'
            "---\n"
            "\n"
            "# Opening Principles\n"
        )
        with pytest.raises(ValidationError, match="last_validated"):
            parse_document("context/chess/opening.md", md)

    def test_plan_missing_status(self):
        md = (
            "---\n"
            "document_type: plan\n"
            'description: "Implementation plan for a four-type document system"\n'
            "last_updated: 2026-02-17\n"
            "---\n"
            "\n"
            "# My Plan\n"
        )
        with pytest.raises(ValidationError, match="status"):
            parse_document("artifacts/plans/2026-02-17-plan.md", md)

    def test_missing_description(self):
        md = (
            "---\n"
            "document_type: plan\n"
            "last_updated: 2026-02-17\n"
            "status: draft\n"
            "---\n"
            "\n"
            "# My Plan\n"
        )
        with pytest.raises(ValidationError, match="description"):
            parse_document("artifacts/plans/2026-02-17-plan.md", md)

    def test_missing_last_updated(self):
        md = (
            "---\n"
            "document_type: plan\n"
            'description: "Implementation plan for a four-type document system"\n'
            "status: draft\n"
            "---\n"
            "\n"
            "# My Plan\n"
        )
        with pytest.raises(ValidationError, match="last_updated"):
            parse_document("artifacts/plans/2026-02-17-plan.md", md)


# ── Field validation ─────────────────────────────────────────────


class TestFieldValidation:
    def test_description_too_short(self):
        with pytest.raises(ValidationError, match="at least 10"):
            parse_document(
                "artifacts/plans/2026-02-17-plan.md",
                _plan_md(description="Too short"),
            )

    def test_future_last_updated_rejected(self):
        with pytest.raises(ValidationError, match="future"):
            parse_document(
                "artifacts/plans/2026-02-17-plan.md",
                _plan_md(last_updated="2099-01-01"),
            )

    def test_future_last_validated_rejected(self):
        with pytest.raises(ValidationError, match="future"):
            parse_document(
                "context/chess/opening.md",
                _topic_md(last_validated="2099-01-01"),
            )

    def test_invalid_plan_status(self):
        with pytest.raises(ValidationError, match="status"):
            parse_document(
                "artifacts/plans/2026-02-17-plan.md",
                _plan_md(status="invalid"),
            )

    def test_tags_must_be_lowercase_hyphenated(self):
        with pytest.raises(ValidationError, match="lowercase hyphenated"):
            parse_document(
                "artifacts/plans/2026-02-17-plan.md",
                _plan_md(extra_fm='tags: ["CamelCase"]\n'),
            )

    def test_valid_tags_accepted(self):
        doc = parse_document(
            "artifacts/plans/2026-02-17-plan.md",
            _plan_md(extra_fm='tags: ["api-design", "caching"]\n'),
        )
        assert doc.frontmatter.tags == ["api-design", "caching"]

    def test_empty_sources_rejected(self):
        md = (
            "---\n"
            "document_type: topic\n"
            'description: "Core principles for the first 10-15 moves of a game"\n'
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            "sources: []\n"
            "---\n"
            "\n"
            "# Opening Principles\n"
        )
        with pytest.raises(ValidationError, match="sources"):
            parse_document("context/chess/opening.md", md)


# ── No frontmatter ───────────────────────────────────────────────


class TestNoFrontmatter:
    def test_no_frontmatter_raises(self):
        md = "# Just a Heading\n\nSome content.\n"
        with pytest.raises(ValidationError, match="frontmatter"):
            parse_document("context/chess/opening.md", md)

    def test_partial_frontmatter_raises(self):
        md = "---\ndocument_type: topic\n\n# Missing closing delimiter\n"
        with pytest.raises(ValidationError, match="frontmatter"):
            parse_document("context/chess/opening.md", md)


# ── Markdown splitting ───────────────────────────────────────────


class TestSplitMarkdown:
    def test_extracts_title(self):
        doc = parse_document("context/chess/opening.md", _topic_md())
        assert doc.title == "Opening Principles"

    def test_extracts_sections(self):
        doc = parse_document("context/chess/opening.md", _topic_md())
        assert set(doc.section_names) == {
            "Guidance",
            "Context",
            "In Practice",
            "Pitfalls",
            "Go Deeper",
        }

    def test_h3_inside_h2(self):
        """H3+ headings are content within their parent H2, not separate sections."""
        md = (
            "---\n"
            "document_type: plan\n"
            'description: "Implementation plan for a four-type document system"\n'
            "last_updated: 2026-02-17\n"
            "status: draft\n"
            "---\n"
            "\n"
            "# My Plan\n"
            "\n"
            "## Objective\n"
            "\n"
            "Build the thing.\n"
            "\n"
            "## Context\n"
            "\n"
            "### Sub-heading within context\n"
            "\n"
            "This is nested content.\n"
            "\n"
            "### Another sub-heading\n"
            "\n"
            "More nested content.\n"
            "\n"
            "## Steps\n"
            "\n"
            "1. Do stuff.\n"
            "\n"
            "## Verification\n"
            "\n"
            "- It works.\n"
        )
        doc = parse_document("artifacts/plans/2026-02-17-plan.md", md)
        assert "Sub-heading within context" in doc.get_section_content("Context")
        assert "Another sub-heading" in doc.get_section_content("Context")
        assert "Sub-heading within context" not in doc.section_names

    def test_preserves_raw_content(self):
        content = _topic_md()
        doc = parse_document("context/chess/opening.md", content)
        assert doc.raw_content == content


# ── Document properties ──────────────────────────────────────────


class TestDocumentProperties:
    def test_required_sections_for_topic(self):
        doc = parse_document("context/chess/opening.md", _topic_md())
        names = [s.name for s in doc.required_sections]
        assert names == ["Guidance", "Context", "In Practice", "Pitfalls", "Go Deeper"]

    def test_size_bounds_for_overview(self):
        doc = parse_document("context/chess/_overview.md", _overview_md())
        assert doc.size_bounds.min_lines == 5
        assert doc.size_bounds.max_lines == 150

    def test_size_bounds_research_no_max(self):
        doc = parse_document(
            "artifacts/research/2026-02-17-doc.md", _research_md()
        )
        assert doc.size_bounds.max_lines is None


# ── Note documents ───────────────────────────────────────────────


class TestNoteDocument:
    def test_note_parses(self):
        doc = parse_document("notes/meeting-facilitation.md", _note_md())
        assert doc.document_type == DocumentType.NOTE
        assert doc.frontmatter.description == (
            "Personal notes on effective meeting facilitation techniques"
        )

    def test_note_minimal_frontmatter(self):
        doc = parse_document("notes/test.md", _note_md())
        assert not hasattr(doc.frontmatter, "last_updated")
        assert not hasattr(doc.frontmatter, "sources")

    def test_note_with_tags(self):
        md = _note_md(extra_fm='tags:\n  - meetings\n  - facilitation\n')
        doc = parse_document("notes/test.md", md)
        assert doc.frontmatter.tags == ["meetings", "facilitation"]

    def test_note_with_related(self):
        md = _note_md(extra_fm='related:\n  - context/area/topic.md\n')
        doc = parse_document("notes/test.md", md)
        assert doc.frontmatter.related == ["context/area/topic.md"]

    def test_note_short_description_rejected(self):
        with pytest.raises(ValidationError):
            parse_document("notes/test.md", _note_md(description="Short"))

    def test_note_any_directory_accepted(self):
        for path in [
            "notes/test.md",
            "context/area/test.md",
            "artifacts/test.md",
            "reading/book.md",
            "recipes/pasta.md",
        ]:
            doc = parse_document(path, _note_md())
            assert doc.document_type == DocumentType.NOTE

    def test_note_no_required_sections(self):
        doc = parse_document("notes/test.md", _note_md())
        assert doc.required_sections == []

    def test_note_size_bounds_minimal(self):
        doc = parse_document("notes/test.md", _note_md())
        assert doc.size_bounds.min_lines == 1
        assert doc.size_bounds.max_lines is None


# ── Type groupings ───────────────────────────────────────────────


class TestTypeGroupings:
    def test_context_types(self):
        assert CONTEXT_TYPES == {DocumentType.OVERVIEW, DocumentType.TOPIC}

    def test_artifact_types(self):
        assert ARTIFACT_TYPES == {DocumentType.RESEARCH, DocumentType.PLAN}

    def test_source_grounded_types(self):
        assert SOURCE_GROUNDED_TYPES == {DocumentType.TOPIC, DocumentType.RESEARCH}

    def test_freshness_tracked_types(self):
        assert FRESHNESS_TRACKED_TYPES == {DocumentType.TOPIC, DocumentType.OVERVIEW}

    def test_date_prefix_types(self):
        assert DATE_PREFIX_TYPES == {DocumentType.RESEARCH, DocumentType.PLAN}

    def test_note_not_in_any_group(self):
        assert DocumentType.NOTE not in CONTEXT_TYPES
        assert DocumentType.NOTE not in ARTIFACT_TYPES
        assert DocumentType.NOTE not in SOURCE_GROUNDED_TYPES
        assert DocumentType.NOTE not in FRESHNESS_TRACKED_TYPES
        assert DocumentType.NOTE not in DATE_PREFIX_TYPES


# ── Directory patterns ───────────────────────────────────────────


class TestDirectoryPatterns:
    def test_topic_pattern_matches(self):
        import re

        pattern = DIRECTORY_PATTERNS[DocumentType.TOPIC]
        assert re.search(pattern, "context/chess/opening-principles.md")
        assert not re.search(pattern, "context/chess/_overview.md")

    def test_overview_pattern_matches_underscore(self):
        import re

        pattern = DIRECTORY_PATTERNS[DocumentType.OVERVIEW]
        assert re.search(pattern, "context/chess/_overview.md")
        assert not re.search(pattern, "context/chess/overview.md")

    def test_research_pattern_matches(self):
        import re

        pattern = DIRECTORY_PATTERNS[DocumentType.RESEARCH]
        assert re.search(pattern, "artifacts/research/2026-02-17-doc-types.md")
        assert re.search(
            pattern,
            "artifacts/research/v0.1-foundation/2026-02-17-doc-types.md",
        )

    def test_plan_pattern_matches(self):
        import re

        pattern = DIRECTORY_PATTERNS[DocumentType.PLAN]
        assert re.search(pattern, "artifacts/plans/2026-02-17-doc-types.md")
        assert re.search(
            pattern,
            "artifacts/plans/v0.1-foundation/2026-02-17-doc-types.md",
        )

    def test_all_types_have_patterns(self):
        for dt in DocumentType:
            if dt in _TYPES_WITHOUT_DIRECTORY_PATTERN:
                continue
            assert dt in DIRECTORY_PATTERNS, f"Missing pattern for {dt}"


# ── Dispatch tables ──────────────────────────────────────────────


class TestDispatchTables:
    def test_all_types_have_sections(self):
        for dt in DocumentType:
            assert dt in SECTIONS, f"Missing sections for {dt}"

    def test_all_types_have_size_bounds(self):
        for dt in DocumentType:
            assert dt in SIZE_BOUNDS, f"Missing size bounds for {dt}"

    def test_section_positions_are_sequential(self):
        for dt, specs in SECTIONS.items():
            positions = [s.position for s in specs]
            assert positions == list(range(1, len(positions) + 1)), (
                f"{dt}: positions should be sequential from 1"
            )

    def test_overview_what_this_covers_has_min_words(self):
        overview_sections = SECTIONS[DocumentType.OVERVIEW]
        wtc = next(s for s in overview_sections if s.name == "What This Covers")
        assert wtc.min_words == 30

    def test_note_not_in_directory_patterns(self):
        assert DocumentType.NOTE not in DIRECTORY_PATTERNS
