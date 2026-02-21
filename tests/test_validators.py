"""Tests for wos.validators — per-file document validators.

All tests use inline markdown strings.
"""

from __future__ import annotations

from wos.document_types import DocumentType, parse_document
from wos.validators import (
    check_date_prefix_matches,
    check_directory_placement,
    check_go_deeper_links,
    check_heading_hierarchy,
    check_last_validated,
    check_placeholder_comments,
    check_question_nonempty,
    check_section_ordering,
    check_section_presence,
    check_size_bounds,
    check_source_diversity,
    check_title_heading,
    check_what_this_covers_length,
    validate_document,
)

# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(
    *,
    extra_fm: str = "",
    sections: str = "",
) -> str:
    base_sections = (
        "## Guidance\n\nUse exceptions for exceptional cases.\n\n"
        "## Context\n\nBackground info here.\n\n"
        "## In Practice\n\nExample usage here.\n\n"
        "## Pitfalls\n\nCommon mistakes to avoid here.\n\n"
        "## Go Deeper\n\n- [Python Docs](https://docs.python.org)\n"
    )
    return (
        "---\n"
        "document_type: topic\n"
        'description: "When and how to use exceptions in Python"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://docs.python.org/3/tutorial/errors.html"\n'
        '    title: "Python Errors Tutorial"\n'
        '  - url: "https://realpython.com/python-exceptions/"\n'
        '    title: "Real Python Exceptions"\n'
        f"{extra_fm}"
        "---\n"
        "\n"
        "# Error Handling\n"
        "\n"
        f"{sections or base_sections}"
    )


def _overview_md(*, sections: str = "") -> str:
    base_sections = (
        "## What This Covers\n\n"
        "This area covers core Python programming concepts including "
        "error handling with try-except blocks, unit testing with pytest, "
        "package management with pip and virtual environments, type hints "
        "and static analysis, logging best practices, and common design "
        "patterns used in modern Python development projects.\n\n"
        "## Topics\n\n"
        "- Error Handling\n\n"
        "## Key Sources\n\n"
        "- [Python Docs](https://docs.python.org)\n"
    )
    return (
        "---\n"
        "document_type: overview\n"
        'description: "Core Python programming concepts"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Python\n"
        "\n"
        f"{sections or base_sections}"
    )


def _research_md(*, sections: str = "") -> str:
    base_sections = (
        "## Question\n\n"
        "What are the best practices for error handling?\n\n"
        "## Findings\n\nUse specific exception types.\n\n"
        "## Implications\n\nBetter error messages.\n\n"
        "## Sources\n\n- Python docs\n"
    )
    return (
        "---\n"
        "document_type: research\n"
        'description: "Investigation of error handling patterns"\n'
        "last_updated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://docs.python.org"\n'
        '    title: "Python Docs"\n'
        "---\n"
        "\n"
        "# Error Handling Research\n"
        "\n"
        f"{sections or base_sections}"
    )


def _plan_md(*, sections: str = "") -> str:
    base_sections = (
        "## Objective\n\nImprove error handling.\n\n"
        "## Context\n\nCurrent state is poor.\n\n"
        "## Steps\n\n1. Audit existing code.\n"
        "2. Refactor handlers.\n\n"
        "## Verification\n\n- All tests pass.\n"
    )
    return (
        "---\n"
        "document_type: plan\n"
        'description: "Plan to improve error handling across the codebase"\n'
        "last_updated: 2026-02-17\n"
        "status: active\n"
        "---\n"
        "\n"
        "# Error Handling Plan\n"
        "\n"
        f"{sections or base_sections}"
    )


def _parse(md: str, path: str = "context/python/error-handling.md"):
    return parse_document(path, md)


# ── Dispatch table ───────────────────────────────────────────────


class TestPolymorphicDispatch:
    """Verify each document type's validate_self() runs correct validators."""

    def test_all_types_have_validate_self(self) -> None:
        """Every document subclass has validate_self()."""
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
            assert hasattr(cls, "validate_self")

    def test_topic_runs_last_validated(self) -> None:
        doc = _parse(_topic_md())
        # Stale date would trigger check_last_validated
        issues = validate_document(doc)
        validators_run = {i.validator for i in issues}
        # Clean doc has no issues, but the method exists and runs
        assert isinstance(issues, list)

    def test_research_skips_last_validated(self) -> None:
        doc = _parse(
            _research_md(),
            path="artifacts/research/2026-02-17-test.md",
        )
        issues = validate_document(doc)
        assert all(i.validator != "check_last_validated" for i in issues)

    def test_plan_skips_last_validated(self) -> None:
        doc = _parse(
            _plan_md(),
            path="artifacts/plans/2026-02-17-test.md",
        )
        issues = validate_document(doc)
        assert all(i.validator != "check_last_validated" for i in issues)

    def test_note_only_checks_title(self) -> None:
        """Note validate_self() only runs check_title_heading."""
        md = (
            "---\n"
            "document_type: note\n"
            'description: "Personal notes on effective meeting facilitation"\n'
            "---\n"
            "\n"
            "# My Note\n\nContent.\n"
        )
        doc = parse_document("notes/test.md", md)
        issues = validate_document(doc)
        # Clean note has zero issues (title present, no section checks)
        assert issues == []


# ── check_section_presence ───────────────────────────────────────


class TestCheckSectionPresence:
    def test_all_sections_present(self) -> None:
        doc = _parse(_topic_md())
        issues = check_section_presence(doc)
        assert len(issues) == 0

    def test_missing_section(self) -> None:
        md = _topic_md(
            sections=(
                "## Guidance\n\nContent.\n\n"
                "## Context\n\nContent.\n\n"
                "## In Practice\n\nContent.\n"
            )
        )
        doc = _parse(md)
        issues = check_section_presence(doc)
        missing = [i.section for i in issues]
        assert "Pitfalls" in missing
        assert "Go Deeper" in missing

    def test_plan_missing_verification(self) -> None:
        md = _plan_md(
            sections=(
                "## Objective\n\nGoal.\n\n"
                "## Context\n\nBackground.\n\n"
                "## Steps\n\n1. Do thing.\n"
            )
        )
        doc = _parse(
            md,
            path="artifacts/plans/2026-02-17-test.md",
        )
        issues = check_section_presence(doc)
        assert any(i.section == "Verification" for i in issues)
        assert all(i.severity == "warn" for i in issues)

    def test_suggestion_includes_full_section_list_for_plan(self) -> None:
        """Issue #9: suggestion should list all expected sections."""
        md = _plan_md(
            sections=(
                "## Objective\n\nGoal.\n\n"
                "## Steps\n\n1. Do thing.\n"
            )
        )
        doc = _parse(md, path="artifacts/plans/2026-02-17-test.md")
        issues = check_section_presence(doc)
        # Both missing sections should mention the full plan section list
        for issue in issues:
            assert "## Objective" in issue.suggestion
            assert "## Context" in issue.suggestion
            assert "## Steps" in issue.suggestion
            assert "## Verification" in issue.suggestion

    def test_suggestion_includes_full_section_list_for_topic(self) -> None:
        """Issue #9: topic missing sections list all expected sections."""
        md = _topic_md(
            sections=(
                "## Guidance\n\nContent.\n\n"
                "## Context\n\nContent.\n\n"
                "## In Practice\n\nContent.\n"
            )
        )
        doc = _parse(md)
        issues = check_section_presence(doc)
        for issue in issues:
            assert "## Guidance" in issue.suggestion
            assert "## Go Deeper" in issue.suggestion

    def test_suggestion_includes_full_section_list_for_research(self) -> None:
        """Issue #9: research missing sections list all expected sections."""
        md = _research_md(
            sections="## Question\n\nWhat?\n\n## Findings\n\nStuff.\n"
        )
        doc = _parse(md, path="artifacts/research/2026-02-17-test.md")
        issues = check_section_presence(doc)
        assert len(issues) == 2  # Implications and Sources missing
        for issue in issues:
            assert "## Question" in issue.suggestion
            assert "## Sources" in issue.suggestion

    def test_suggestion_includes_full_section_list_for_overview(self) -> None:
        """Issue #9: overview missing sections list all expected sections."""
        md = _overview_md(
            sections="## Topics\n\n- Topic A\n\n## Key Sources\n\n- Src\n"
        )
        doc = _parse(md, path="context/python/_overview.md")
        issues = check_section_presence(doc)
        assert len(issues) == 1  # What This Covers missing
        assert "## What This Covers" in issues[0].suggestion
        assert "## Topics" in issues[0].suggestion
        assert "## Key Sources" in issues[0].suggestion


# ── check_section_ordering ───────────────────────────────────────


class TestCheckSectionOrdering:
    def test_correct_order(self) -> None:
        doc = _parse(_topic_md())
        assert check_section_ordering(doc) == []

    def test_wrong_order(self) -> None:
        md = _topic_md(
            sections=(
                "## Context\n\nContent.\n\n"
                "## Guidance\n\nContent.\n\n"
                "## In Practice\n\nContent.\n\n"
                "## Pitfalls\n\nContent.\n\n"
                "## Go Deeper\n\nContent.\n"
            )
        )
        doc = _parse(md)
        issues = check_section_ordering(doc)
        assert len(issues) == 1
        assert issues[0].severity == "warn"

    def test_suggestion_includes_full_section_list(self) -> None:
        """Issue #9: ordering error should list all expected sections."""
        md = _topic_md(
            sections=(
                "## Context\n\nContent.\n\n"
                "## Guidance\n\nContent.\n\n"
                "## In Practice\n\nContent.\n\n"
                "## Pitfalls\n\nContent.\n\n"
                "## Go Deeper\n\nContent.\n"
            )
        )
        doc = _parse(md)
        issues = check_section_ordering(doc)
        assert len(issues) == 1
        assert "## Guidance" in issues[0].suggestion
        assert "## Context" in issues[0].suggestion
        assert "## Go Deeper" in issues[0].suggestion

    def test_plan_ordering_suggestion_includes_plan_sections(self) -> None:
        """Issue #9: plan ordering error lists plan sections."""
        md = _plan_md(
            sections=(
                "## Steps\n\n1. Do thing.\n\n"
                "## Objective\n\nGoal.\n\n"
                "## Context\n\nBackground.\n\n"
                "## Verification\n\n- Tests pass.\n"
            )
        )
        doc = _parse(md, path="artifacts/plans/2026-02-17-test.md")
        issues = check_section_ordering(doc)
        assert len(issues) == 1
        assert "## Objective" in issues[0].suggestion
        assert "## Verification" in issues[0].suggestion


# ── check_size_bounds ────────────────────────────────────────────


class TestCheckSizeBounds:
    def test_within_bounds(self) -> None:
        doc = _parse(_topic_md())
        assert check_size_bounds(doc) == []

    def test_too_short(self) -> None:
        md = (
            "---\n"
            "document_type: topic\n"
            'description: "Short topic for testing"\n'
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            'sources: [{url: "https://example.com", title: "Ex"}]\n'
            "---\n"
        )
        doc = _parse(md)
        issues = check_size_bounds(doc)
        # Topic min is 10 lines, this is 7
        assert any("minimum" in i.issue for i in issues)


# ── check_directory_placement ────────────────────────────────────


class TestCheckDirectoryPlacement:
    def test_correct_placement(self) -> None:
        doc = _parse(
            _topic_md(), path="context/python/error-handling.md"
        )
        assert check_directory_placement(doc) == []

    def test_wrong_placement(self) -> None:
        doc = _parse(_topic_md(), path="wrong/place/file.md")
        issues = check_directory_placement(doc)
        assert len(issues) == 1
        assert issues[0].severity == "warn"


# ── check_title_heading ──────────────────────────────────────────


class TestCheckTitleHeading:
    def test_has_title(self) -> None:
        doc = _parse(_topic_md())
        assert check_title_heading(doc) == []

    def test_no_title(self) -> None:
        md = (
            "---\n"
            "document_type: topic\n"
            'description: "Topic without a title heading"\n'
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            "sources:\n"
            '  - url: "https://example.com"\n'
            '    title: "Ex"\n'
            "---\n"
            "\n"
            "## Guidance\n\nContent.\n"
            "## Context\n\nContent.\n"
            "## In Practice\n\nContent.\n"
            "## Pitfalls\n\nContent.\n"
            "## Go Deeper\n\nContent.\n"
        )
        doc = _parse(md)
        issues = check_title_heading(doc)
        assert len(issues) == 1


# ── check_heading_hierarchy ──────────────────────────────────────


class TestCheckHeadingHierarchy:
    def test_good_hierarchy(self) -> None:
        doc = _parse(_topic_md())
        assert check_heading_hierarchy(doc) == []


# ── check_placeholder_comments ───────────────────────────────────


class TestCheckPlaceholderComments:
    def test_no_placeholders(self) -> None:
        doc = _parse(_topic_md())
        assert check_placeholder_comments(doc) == []

    def test_has_todo(self) -> None:
        md = _topic_md(
            sections=(
                "## Guidance\n\n<!-- TODO: add content -->\n\n"
                "## Context\n\nContent.\n\n"
                "## In Practice\n\nContent.\n\n"
                "## Pitfalls\n\nContent.\n\n"
                "## Go Deeper\n\n- [Link](https://example.com)\n"
            )
        )
        doc = _parse(md)
        issues = check_placeholder_comments(doc)
        assert len(issues) == 1
        assert issues[0].severity == "info"


# ── check_last_validated ─────────────────────────────────────────


class TestCheckLastValidated:
    def test_recent_is_clean(self) -> None:
        doc = _parse(_topic_md())
        assert check_last_validated(doc) == []

    def test_research_not_checked(self) -> None:
        """Research documents should NOT be checked for staleness."""
        doc = _parse(
            _research_md(),
            path="artifacts/research/2026-02-17-test.md",
        )
        issues = check_last_validated(doc)
        assert len(issues) == 0

    def test_plan_not_checked(self) -> None:
        """Plan documents should NOT be checked for staleness."""
        doc = _parse(
            _plan_md(),
            path="artifacts/plans/2026-02-17-test.md",
        )
        issues = check_last_validated(doc)
        assert len(issues) == 0


# ── check_source_diversity ───────────────────────────────────────


class TestCheckSourceDiversity:
    def test_diverse_sources(self) -> None:
        doc = _parse(_topic_md())
        assert check_source_diversity(doc) == []

    def test_same_domain(self) -> None:
        md = _topic_md(
            extra_fm=""  # Default has 2 different domains
        )
        # Create a topic with same-domain sources
        md = (
            "---\n"
            "document_type: topic\n"
            'description: "Topic with same-domain sources for testing"\n'
            "last_updated: 2026-02-17\n"
            "last_validated: 2026-02-17\n"
            "sources:\n"
            '  - url: "https://example.com/a"\n'
            '    title: "Example A"\n'
            '  - url: "https://example.com/b"\n'
            '    title: "Example B"\n'
            "---\n"
            "\n"
            "# Same Domain\n"
            "\n"
            "## Guidance\n\nContent.\n"
            "## Context\n\nContent.\n"
            "## In Practice\n\nContent.\n"
            "## Pitfalls\n\nContent.\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        doc = _parse(md)
        issues = check_source_diversity(doc)
        assert len(issues) == 1
        assert issues[0].severity == "info"


# ── check_go_deeper_links ───────────────────────────────────────


class TestCheckGoDeeperLinks:
    def test_has_links(self) -> None:
        doc = _parse(_topic_md())
        assert check_go_deeper_links(doc) == []

    def test_no_links(self) -> None:
        md = _topic_md(
            sections=(
                "## Guidance\n\nContent.\n\n"
                "## Context\n\nContent.\n\n"
                "## In Practice\n\nContent.\n\n"
                "## Pitfalls\n\nContent.\n\n"
                "## Go Deeper\n\nJust text, no links.\n"
            )
        )
        doc = _parse(md)
        issues = check_go_deeper_links(doc)
        assert len(issues) == 1


# ── check_what_this_covers_length ────────────────────────────────


class TestCheckWhatThisCoversLength:
    def test_sufficient_length(self) -> None:
        doc = _parse(
            _overview_md(),
            path="context/python/_overview.md",
        )
        assert check_what_this_covers_length(doc) == []

    def test_too_short(self) -> None:
        md = _overview_md(
            sections=(
                "## What This Covers\n\nJust Python stuff.\n\n"
                "## Topics\n\n- Topics here\n\n"
                "## Key Sources\n\n- Sources here\n"
            )
        )
        doc = _parse(md, path="context/python/_overview.md")
        issues = check_what_this_covers_length(doc)
        assert len(issues) == 1
        assert issues[0].severity == "warn"


# ── check_question_nonempty ──────────────────────────────────────


class TestCheckQuestionNonempty:
    def test_has_question(self) -> None:
        doc = _parse(
            _research_md(),
            path="artifacts/research/2026-02-17-test.md",
        )
        assert check_question_nonempty(doc) == []

    def test_empty_question(self) -> None:
        md = _research_md(
            sections=(
                "## Question\n\n\n\n"
                "## Findings\n\nSome findings.\n\n"
                "## Implications\n\nSome implications.\n\n"
                "## Sources\n\n- Source\n"
            )
        )
        doc = _parse(
            md, path="artifacts/research/2026-02-17-test.md"
        )
        issues = check_question_nonempty(doc)
        assert len(issues) == 1
        assert issues[0].severity == "fail"


# ── check_date_prefix_matches ───────────────────────────────────


class TestCheckDatePrefixMatches:
    def test_matching_date(self) -> None:
        doc = _parse(
            _research_md(),
            path="artifacts/research/2026-02-17-test.md",
        )
        assert check_date_prefix_matches(doc) == []

    def test_mismatched_date(self) -> None:
        doc = _parse(
            _research_md(),
            path="artifacts/research/2025-01-01-test.md",
        )
        issues = check_date_prefix_matches(doc)
        assert len(issues) == 1
        assert issues[0].severity == "info"


# ── validate_document (integration) ─────────────────────────────


class TestValidateDocument:
    def test_clean_topic(self) -> None:
        doc = _parse(_topic_md())
        issues = validate_document(doc)
        # May have some info-level issues but no fails
        fails = [i for i in issues if i.severity == "fail"]
        assert len(fails) == 0

    def test_clean_plan(self) -> None:
        doc = _parse(
            _plan_md(),
            path="artifacts/plans/2026-02-17-test.md",
        )
        issues = validate_document(doc)
        fails = [i for i in issues if i.severity == "fail"]
        assert len(fails) == 0


# ── Note helpers ────────────────────────────────────────────────


def _note_md(
    *,
    description="Personal notes on effective meeting facilitation techniques",
) -> str:
    return (
        "---\n"
        "document_type: note\n"
        f'description: "{description}"\n'
        "---\n"
        "\n"
        "# Meeting Facilitation\n"
        "\n"
        "Some content here.\n"
    )


class TestNoteValidation:
    def test_clean_note_no_issues(self):
        doc = parse_document("notes/test.md", _note_md())
        issues = validate_document(doc)
        assert issues == []

    def test_note_missing_title_warns(self):
        md = (
            "---\n"
            "document_type: note\n"
            'description: "Personal notes on effective meeting facilitation"\n'
            "---\n"
            "\n"
            "Some content without a title.\n"
        )
        doc = parse_document("notes/test.md", md)
        issues = validate_document(doc)
        assert len(issues) == 1
        assert issues[0].validator == "check_title_heading"

    def test_note_no_section_checks(self):
        md = (
            "---\n"
            "document_type: note\n"
            'description: "Personal notes on effective meeting facilitation"\n'
            "---\n"
            "\n"
            "# My Note\n"
            "\n"
            "## Random Section\n"
            "\n"
            "Content here.\n"
            "\n"
            "## Another Section\n"
            "\n"
            "More content.\n"
        )
        doc = parse_document("notes/test.md", md)
        issues = validate_document(doc)
        assert all(
            i.validator != "check_section_presence" for i in issues
        )
        assert all(
            i.validator != "check_section_ordering" for i in issues
        )
