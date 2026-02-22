"""Tests for wos.tier2_triggers — Tier 2 pre-screener triggers."""

from __future__ import annotations

from wos.document_types import DocumentType, parse_document
from wos.tier2_triggers import (
    run_triggers,
    trigger_description_quality,
    trigger_verification_completeness,
)

# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(desc: str = "When and how to use exceptions in Python"):
    return (
        "---\n"
        "document_type: topic\n"
        f'description: "{desc}"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Topic\n"
        "\n"
        "## Guidance\n\nDetailed guidance here.\n\n"
        "## Context\n\nBackground context.\n\n"
        "## In Practice\n\n"
        "```python\ntry:\n    pass\nexcept ValueError:\n    pass\n```\n\n"
        "## Pitfalls\n\nCommon mistakes to avoid in error handling.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )


def _plan_md(verification: str = "- All tests pass.\n- Linting clean.\n"):
    return (
        "---\n"
        "document_type: plan\n"
        'description: "Plan to improve error handling across codebase"\n'
        "last_updated: 2026-02-17\n"
        "status: active\n"
        "---\n"
        "\n"
        "# Plan\n"
        "\n"
        "## Objective\n\nImprove error handling.\n\n"
        "## Context\n\nCurrent state.\n\n"
        "## Steps\n\n1. Audit.\n2. Refactor.\n\n"
        f"## Verification\n\n{verification}"
    )


# ── Polymorphic dispatch ─────────────────────────────────────────


class TestPolymorphicDispatch:
    def test_all_subclasses_have_validate_content(self) -> None:
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
            assert hasattr(cls, "validate_content")

    def test_shared_trigger_runs_for_topic(self) -> None:
        from wos.models.core import ValidationIssue

        doc = parse_document(
            "context/python/topic.md",
            _topic_md(desc="Short desc here"),
        )
        results = run_triggers(doc)
        # Base validate_content() now returns ValidationIssue objects
        desc_issues = [
            r for r in results
            if isinstance(r, ValidationIssue)
            and r.validator == "validate_content"
        ]
        assert len(desc_issues) > 0


# ── trigger_description_quality ──────────────────────────────────


class TestTriggerDescriptionQuality:
    def test_good_description(self) -> None:
        doc = parse_document(
            "context/python/topic.md", _topic_md()
        )
        assert trigger_description_quality(doc) == []

    def test_short_description(self) -> None:
        doc = parse_document(
            "context/python/topic.md",
            _topic_md(desc="Short desc here"),
        )
        triggers = trigger_description_quality(doc)
        assert len(triggers) == 1
        assert triggers[0]["trigger"] == "description_quality"


# ── trigger_verification_completeness ────────────────────────────


class TestTriggerVerificationCompleteness:
    def test_sufficient_verification(self) -> None:
        doc = parse_document(
            "artifacts/plans/2026-02-17-test.md",
            _plan_md(),
        )
        assert trigger_verification_completeness(doc) == []

    def test_sparse_verification(self) -> None:
        doc = parse_document(
            "artifacts/plans/2026-02-17-test.md",
            _plan_md(verification="- Tests pass.\n"),
        )
        triggers = trigger_verification_completeness(doc)
        assert len(triggers) == 1


# ── run_triggers (integration) ───────────────────────────────────


class TestRunTriggers:
    def test_returns_list(self) -> None:
        doc = parse_document(
            "context/python/topic.md", _topic_md()
        )
        result = run_triggers(doc)
        assert isinstance(result, list)


class TestNoteTriggers:
    def test_note_validate_content_empty(self):
        md = (
            "---\n"
            "document_type: note\n"
            'description: "Personal notes on a specific topic area"\n'
            "---\n\n# My Note\n\nContent.\n"
        )
        doc = parse_document("notes/test.md", md)
        assert run_triggers(doc) == []
