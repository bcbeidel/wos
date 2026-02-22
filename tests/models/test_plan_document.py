"""Tests for PlanDocument validate_content()."""
from __future__ import annotations

from wos.models.parsing import parse_document


def _make_plan(
    steps=(
        "1. Do first thing in detail with clear instructions "
        "and make sure all prerequisites are met.\n"
        "2. Do second thing with all needed context "
        "and verify the output matches expected format.\n"
    ),
    verification="- Check output matches expected.\n- Verify no regressions.\n",
):
    md = (
        "---\n"
        "document_type: plan\n"
        'description: "Test plan document"\n'
        "last_updated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Test Plan\n"
        "\n"
        "## Objective\n\nAccomplish the goal.\n"
        "\n"
        "## Context\n\nBackground info here.\n"
        "\n"
        f"## Steps\n\n{steps}"
        "\n"
        f"## Verification\n\n{verification}"
    )
    return parse_document("artifacts/plans/2026-02-17-test.md", md)


class TestPlanValidateContent:
    def test_vague_steps_flags_review(self):
        doc = _make_plan(steps="1. Do it.\n2. Test.\n3. Ship.\n")
        issues = doc.validate_content()
        step_issues = [i for i in issues if i.section == "Steps"]
        assert len(step_issues) > 0
        assert all(i.requires_llm for i in step_issues)

    def test_sparse_verification_flags_review(self):
        doc = _make_plan(verification="- Works.\n")
        issues = doc.validate_content()
        v_issues = [i for i in issues if i.section == "Verification"]
        assert len(v_issues) > 0
        assert all(i.requires_llm for i in v_issues)

    def test_good_plan_no_content_issues(self):
        doc = _make_plan()
        issues = doc.validate_content()
        section_issues = [i for i in issues if i.section in ("Steps", "Verification")]
        assert len(section_issues) == 0
