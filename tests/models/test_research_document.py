"""Tests for ResearchDocument validate_content()."""
from __future__ import annotations

from wos.models.parsing import parse_document
from wos.models.core import ValidationIssue


def _make_research(
    question="What is the best approach?",
    findings="Based on [Source](https://example.com), the approach works well.\n",
):
    md = (
        "---\n"
        "document_type: research\n"
        'description: "Test research document"\n'
        "last_updated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Test Research\n"
        "\n"
        f"## Question\n\n{question}\n"
        "\n"
        f"## Findings\n\n{findings}"
        "\n"
        "## Implications\n\nThis means we should do X.\n"
    )
    return parse_document("artifacts/research/2026-02-17-test.md", md)


class TestResearchValidateContent:
    def test_question_no_question_mark_flags_review(self):
        doc = _make_research(question="Investigate the pattern")
        issues = doc.validate_content()
        q_issues = [i for i in issues if i.section == "Question"]
        assert len(q_issues) > 0
        assert all(i.requires_llm for i in q_issues)

    def test_findings_no_links_flags_review(self):
        long_text = "The results show that this approach works. " * 10
        doc = _make_research(findings=long_text)
        issues = doc.validate_content()
        f_issues = [i for i in issues if i.section == "Findings"]
        assert len(f_issues) > 0
        assert all(i.requires_llm for i in f_issues)

    def test_good_research_no_content_issues(self):
        doc = _make_research()
        issues = doc.validate_content()
        section_issues = [i for i in issues if i.section in ("Question", "Findings")]
        assert len(section_issues) == 0
