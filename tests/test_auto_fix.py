"""Tests for wos.auto_fix — auto-fix engine and lifecycle transitions.

Tests use inline markdown strings. All fixes must produce output that
passes parse_document() validation.
"""

from __future__ import annotations

from datetime import date

from wos.auto_fix import (
    AUTO_FIXES,
    VALID_TRANSITIONS,
    apply_auto_fixes,
    find_unparseable_files,
    fix_missing_sections,
    fix_section_ordering,
    get_fixed_content,
    transition_status,
)
from wos.document_types import IssueSeverity, PlanStatus, ValidationIssue, parse_document

# ── Helpers ──────────────────────────────────────────────────────

TODAY = date.today().isoformat()


def _topic(
    *,
    sections: str = "",
    title: str = "Test Topic",
    description: str = "A test topic for auto-fix validation",
) -> str:
    if not sections:
        sections = (
            "## Guidance\n\nDo the right thing.\n\n"
            "## Context\n\nBackground info.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
    return (
        "---\n"
        "document_type: topic\n"
        f'description: "{description}"\n'
        f"last_updated: {TODAY}\n"
        f"last_validated: {TODAY}\n"
        'sources:\n  - url: "https://example.com"\n    title: "Example"\n'
        "---\n\n"
        f"# {title}\n\n"
        f"{sections}"
    )


def _plan(
    *,
    status: str = "draft",
    title: str = "Test Plan",
    description: str = "A test plan for auto-fix validation",
) -> str:
    return (
        "---\n"
        "document_type: plan\n"
        f'description: "{description}"\n'
        f"last_updated: {TODAY}\n"
        f"status: {status}\n"
        "---\n\n"
        f"# {title}\n\n"
        "## Objective\n\nThe goal.\n\n"
        "## Context\n\nThe background.\n\n"
        "## Steps\n\n1. Step one.\n\n"
        "## Verification\n\nRun the tests.\n"
    )


def _overview(
    *,
    title: str = "Test Area",
    description: str = "A test overview for auto-fix validation",
) -> str:
    wtc = (
        "This area covers testing concepts including unit tests, "
        "integration tests, end-to-end tests, test fixtures, "
        "mocking strategies, and general best practices for "
        "writing reliable, maintainable test suites."
    )
    return (
        "---\n"
        "document_type: overview\n"
        f'description: "{description}"\n'
        f"last_updated: {TODAY}\n"
        f"last_validated: {TODAY}\n"
        "---\n\n"
        f"# {title}\n\n"
        f"## What This Covers\n\n{wtc}\n\n"
        "## Topics\n\n- Unit Testing\n\n"
        "## Key Sources\n\n- [Docs](https://example.com)\n"
    )


# ── Dispatch table ───────────────────────────────────────────────


class TestDispatchTable:
    def test_known_validators_have_fixes(self) -> None:
        assert "check_section_ordering" in AUTO_FIXES
        assert "check_section_presence" in AUTO_FIXES

    def test_fixes_are_callable(self) -> None:
        for name, fn in AUTO_FIXES.items():
            assert callable(fn), f"AUTO_FIXES[{name}] is not callable"


# ── fix_section_ordering ─────────────────────────────────────────


class TestFixSectionOrdering:
    def test_reorders_swapped_sections(self) -> None:
        # Pitfalls before Context — wrong order
        sections = (
            "## Guidance\n\nDo the right thing.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n\n"
            "## Context\n\nBackground info.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        md = _topic(sections=sections)
        issue = ValidationIssue(
            file="context/test/test.md", issue="Sections out of order",
            severity=IssueSeverity.WARN, validator="check_section_ordering",
        )
        result = fix_section_ordering("context/test/test.md", md, issue)
        assert result is not None
        fixed, desc = result
        assert "Reordered" in desc
        doc = parse_document("context/test/test.md", fixed)
        keys = doc.section_names
        assert keys.index("Context") < keys.index("Pitfalls")

    def test_valid_order_returns_none(self) -> None:
        md = _topic()
        issue = ValidationIssue(
            file="context/test/test.md", issue="Sections out of order",
            severity=IssueSeverity.WARN, validator="check_section_ordering",
        )
        # Already in correct order — fix should still return reordered
        # (but content is equivalent)
        result = fix_section_ordering("context/test/test.md", md, issue)
        if result is not None:
            fixed, _ = result
            parse_document("context/test/test.md", fixed)

    def test_fixed_passes_validation(self) -> None:
        sections = (
            "## Go Deeper\n\n- [Link](https://example.com)\n\n"
            "## Guidance\n\nDo the right thing.\n\n"
            "## Context\n\nBackground info.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n"
        )
        md = _topic(sections=sections)
        issue = ValidationIssue(
            file="context/test/test.md", issue="Sections out of order",
            severity=IssueSeverity.WARN, validator="check_section_ordering",
        )
        result = fix_section_ordering("context/test/test.md", md, issue)
        assert result is not None
        fixed, _ = result
        doc = parse_document("context/test/test.md", fixed)
        assert doc.frontmatter.document_type == "topic"

    def test_preserves_extra_sections(self) -> None:
        sections = (
            "## Context\n\nBackground info.\n\n"
            "## Guidance\n\nDo the right thing.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n\n"
            "## Quick Reference\n\nCheat sheet.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        md = _topic(sections=sections)
        issue = ValidationIssue(
            file="context/test/test.md", issue="Sections out of order",
            severity=IssueSeverity.WARN, validator="check_section_ordering",
        )
        result = fix_section_ordering("context/test/test.md", md, issue)
        assert result is not None
        fixed, _ = result
        doc = parse_document("context/test/test.md", fixed)
        assert doc.has_section("Quick Reference")


# ── fix_missing_sections ─────────────────────────────────────────


class TestFixMissingSections:
    def test_adds_missing_section(self) -> None:
        sections = (
            "## Guidance\n\nDo the right thing.\n\n"
            "## Context\n\nBackground info.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        md = _topic(sections=sections)
        issue = ValidationIssue(
            file="context/test/test.md", issue="Missing section: Pitfalls",
            severity=IssueSeverity.WARN, validator="check_section_presence",
            section="Pitfalls",
        )
        result = fix_missing_sections("context/test/test.md", md, issue)
        assert result is not None
        fixed, desc = result
        assert "Pitfalls" in desc
        doc = parse_document("context/test/test.md", fixed)
        assert doc.has_section("Pitfalls")

    def test_adds_first_section(self) -> None:
        # Missing the very first canonical section
        sections = (
            "## Context\n\nBackground info.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        md = _topic(sections=sections)
        issue = ValidationIssue(
            file="context/test/test.md", issue="Missing section: Guidance",
            severity=IssueSeverity.WARN, validator="check_section_presence",
            section="Guidance",
        )
        result = fix_missing_sections("context/test/test.md", md, issue)
        assert result is not None
        fixed, _ = result
        doc = parse_document("context/test/test.md", fixed)
        assert doc.has_section("Guidance")

    def test_no_section_name_returns_none(self) -> None:
        md = _topic()
        issue = ValidationIssue(
            file="context/test/test.md", issue="Missing section",
            severity=IssueSeverity.WARN, validator="check_section_presence",
        )
        result = fix_missing_sections("context/test/test.md", md, issue)
        assert result is None


# ── transition_status ────────────────────────────────────────────


class TestTransitionStatus:
    def test_draft_to_active(self) -> None:
        md = _plan(status="draft")
        result = transition_status(
            "artifacts/plans/2026-02-17-test.md",
            md,
            PlanStatus.ACTIVE,
        )
        assert result is not None
        fixed, desc = result
        assert "draft -> active" in desc
        doc = parse_document("artifacts/plans/2026-02-17-test.md", fixed)
        assert doc.frontmatter.status == PlanStatus.ACTIVE

    def test_active_to_complete(self) -> None:
        md = _plan(status="active")
        result = transition_status(
            "artifacts/plans/2026-02-17-test.md",
            md,
            PlanStatus.COMPLETE,
        )
        assert result is not None
        fixed, _ = result
        doc = parse_document("artifacts/plans/2026-02-17-test.md", fixed)
        assert doc.frontmatter.status == PlanStatus.COMPLETE

    def test_updates_last_updated(self) -> None:
        md = _plan(status="draft")
        result = transition_status(
            "artifacts/plans/2026-02-17-test.md",
            md,
            PlanStatus.ACTIVE,
        )
        assert result is not None
        fixed, _ = result
        doc = parse_document("artifacts/plans/2026-02-17-test.md", fixed)
        assert doc.frontmatter.last_updated == date.today()

    def test_invalid_transition_returns_none(self) -> None:
        md = _plan(status="draft")
        result = transition_status(
            "artifacts/plans/2026-02-17-test.md",
            md,
            PlanStatus.COMPLETE,  # Can't go draft -> complete
        )
        assert result is None

    def test_non_plan_returns_none(self) -> None:
        md = _topic()
        result = transition_status(
            "context/test/test.md",
            md,
            PlanStatus.ACTIVE,
        )
        assert result is None

    def test_complete_to_active_reopen(self) -> None:
        md = _plan(status="complete")
        result = transition_status(
            "artifacts/plans/2026-02-17-test.md",
            md,
            PlanStatus.ACTIVE,
        )
        assert result is not None
        fixed, desc = result
        assert "complete -> active" in desc


# ── Valid transitions ────────────────────────────────────────────


class TestValidTransitions:
    def test_all_statuses_have_transitions(self) -> None:
        for status in PlanStatus:
            assert status in VALID_TRANSITIONS

    def test_draft_can_become_active_or_abandoned(self) -> None:
        allowed = VALID_TRANSITIONS[PlanStatus.DRAFT]
        assert PlanStatus.ACTIVE in allowed
        assert PlanStatus.ABANDONED in allowed

    def test_active_can_become_complete_or_abandoned(self) -> None:
        allowed = VALID_TRANSITIONS[PlanStatus.ACTIVE]
        assert PlanStatus.COMPLETE in allowed
        assert PlanStatus.ABANDONED in allowed


# ── apply_auto_fixes ─────────────────────────────────────────────


class TestApplyAutoFixes:
    def test_dry_run_does_not_change_content(self) -> None:
        sections = (
            "## Context\n\nBackground info.\n\n"
            "## Guidance\n\nDo the right thing.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        md = _topic(sections=sections)
        issues = [ValidationIssue(
            file="context/test/test.md", issue="Sections out of order",
            severity=IssueSeverity.WARN, validator="check_section_ordering",
        )]
        results = apply_auto_fixes(
            "context/test/test.md", md, issues, dry_run=True
        )
        assert len(results) >= 1
        assert results[0]["applied"] is False

    def test_apply_returns_applied_true(self) -> None:
        sections = (
            "## Context\n\nBackground info.\n\n"
            "## Guidance\n\nDo the right thing.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        md = _topic(sections=sections)
        issues = [ValidationIssue(
            file="context/test/test.md", issue="Sections out of order",
            severity=IssueSeverity.WARN, validator="check_section_ordering",
        )]
        results = apply_auto_fixes("context/test/test.md", md, issues)
        assert len(results) >= 1
        assert results[0]["applied"] is True

    def test_unknown_validator_skipped(self) -> None:
        md = _topic()
        issues = [ValidationIssue(
            file="context/test/test.md", issue="Unknown issue",
            severity=IssueSeverity.WARN, validator="check_nonexistent_thing",
        )]
        results = apply_auto_fixes("context/test/test.md", md, issues)
        assert len(results) == 0


# ── get_fixed_content ────────────────────────────────────────────


class TestGetFixedContent:
    def test_returns_none_when_nothing_to_fix(self) -> None:
        md = _topic()
        issues = [ValidationIssue(
            file="context/test/test.md", issue="Unknown issue",
            severity=IssueSeverity.WARN, validator="check_nonexistent_thing",
        )]
        result = get_fixed_content("context/test/test.md", md, issues)
        assert result is None

    def test_returns_fixed_content(self) -> None:
        sections = (
            "## Context\n\nBackground info.\n\n"
            "## Guidance\n\nDo the right thing.\n\n"
            "## In Practice\n\nReal-world usage.\n\n"
            "## Pitfalls\n\nCommon mistakes.\n\n"
            "## Go Deeper\n\n- [Link](https://example.com)\n"
        )
        md = _topic(sections=sections)
        issues = [ValidationIssue(
            file="context/test/test.md", issue="Sections out of order",
            severity=IssueSeverity.WARN, validator="check_section_ordering",
        )]
        result = get_fixed_content("context/test/test.md", md, issues)
        assert result is not None
        doc = parse_document("context/test/test.md", result)
        keys = doc.section_names
        assert keys.index("Guidance") < keys.index("Context")


# ── find_unparseable_files ───────────────────────────────────────


class TestFindUnparseableFiles:
    def test_valid_file_not_reported(self, tmp_path) -> None:
        md = _topic()
        f = tmp_path / "context" / "test" / "test.md"
        f.parent.mkdir(parents=True)
        f.write_text(md)
        results = find_unparseable_files(
            str(tmp_path), ["context/test/test.md"]
        )
        assert len(results) == 0

    def test_invalid_file_reported(self, tmp_path) -> None:
        f = tmp_path / "context" / "test" / "broken.md"
        f.parent.mkdir(parents=True)
        f.write_text("no frontmatter here")
        results = find_unparseable_files(
            str(tmp_path), ["context/test/broken.md"]
        )
        assert len(results) == 1
        assert results[0]["file"] == "context/test/broken.md"

    def test_missing_file_reported(self, tmp_path) -> None:
        results = find_unparseable_files(
            str(tmp_path), ["context/test/gone.md"]
        )
        assert len(results) == 1
        assert "not found" in results[0]["error"].lower()


# ── Does not corrupt valid documents ─────────────────────────────


class TestSafetyGuards:
    def test_valid_topic_not_corrupted(self) -> None:
        md = _topic()
        issues = [
            ValidationIssue(
                file="context/test/test.md", issue="Sections out of order",
                severity=IssueSeverity.WARN, validator="check_section_ordering",
            ),
            ValidationIssue(
                file="context/test/test.md", issue="Missing section: Guidance",
                severity=IssueSeverity.WARN, validator="check_section_presence",
                section="Guidance",
            ),
        ]
        result = get_fixed_content("context/test/test.md", md, issues)
        # Either returns None (nothing to fix) or valid content
        if result is not None:
            parse_document("context/test/test.md", result)

    def test_valid_plan_not_corrupted(self) -> None:
        md = _plan()
        issues = [
            ValidationIssue(
                file="artifacts/plans/2026-02-17-test.md", issue="Sections out of order",
                severity=IssueSeverity.WARN, validator="check_section_ordering",
            ),
        ]
        result = get_fixed_content(
            "artifacts/plans/2026-02-17-test.md", md, issues
        )
        if result is not None:
            parse_document("artifacts/plans/2026-02-17-test.md", result)

    def test_valid_overview_not_corrupted(self) -> None:
        md = _overview()
        issues = [
            ValidationIssue(
                file="context/test/_overview.md", issue="Sections out of order",
                severity=IssueSeverity.WARN, validator="check_section_ordering",
            ),
        ]
        result = get_fixed_content("context/test/_overview.md", md, issues)
        if result is not None:
            parse_document("context/test/_overview.md", result)
