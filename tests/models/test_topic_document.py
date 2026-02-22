"""Tests for TopicDocument validate_content()."""
from __future__ import annotations

from wos.models.core import ValidationIssue
from wos.models.parsing import parse_document


def _make_topic(
    in_practice="- Do this step.\n- Then this.\n",
    pitfalls=(
        "Watch out for these common mistakes that developers "
        "make when working with this pattern. "
        "Avoid premature optimization and always measure.\n"
    ),
    go_deeper="- [Link](https://example.com)\n",
):
    md = (
        "---\n"
        "document_type: topic\n"
        'description: "A test topic with enough words to pass quality"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Test Topic\n"
        "\n"
        "## Guidance\n\nFollow these steps.\n"
        "\n"
        "## Context\n\nBackground info.\n"
        "\n"
        f"## In Practice\n\n{in_practice}"
        "\n"
        f"## Pitfalls\n\n{pitfalls}"
        "\n"
        f"## Go Deeper\n\n{go_deeper}"
    )
    return parse_document("context/testing/example.md", md)


class TestTopicValidateContent:
    def test_good_topic_no_content_issues(self):
        doc = _make_topic()
        issues = doc.validate_content()
        section_issues = [i for i in issues if i.section in ("In Practice", "Pitfalls")]
        assert len(section_issues) == 0

    def test_in_practice_no_code_or_list_flags_review(self):
        doc = _make_topic(in_practice="Just some prose without examples.\n")
        issues = doc.validate_content()
        in_practice = [i for i in issues if i.section == "In Practice"]
        assert len(in_practice) > 0
        assert all(i.requires_llm for i in in_practice)

    def test_pitfalls_too_short_flags_review(self):
        doc = _make_topic(pitfalls="Be careful.\n")
        issues = doc.validate_content()
        pitfall = [i for i in issues if i.section == "Pitfalls"]
        assert len(pitfall) > 0
        assert all(i.requires_llm for i in pitfall)

    def test_all_content_issues_are_validation_issues(self):
        doc = _make_topic(in_practice="Prose only.\n", pitfalls="Short.\n")
        issues = doc.validate_content()
        for issue in issues:
            assert isinstance(issue, ValidationIssue)
            assert issue.requires_llm is True
