"""Tests for wos.token_budget — token budget estimation.

All tests use inline markdown strings.
"""

from __future__ import annotations

from wos.document_types import parse_document
from wos.token_budget import estimate_token_budget

# ── Helpers ──────────────────────────────────────────────────────


def _topic_md(word_count: int = 50) -> str:
    """Build a minimal topic with approximately word_count words of content."""
    words = " ".join(["word"] * word_count)
    return (
        "---\n"
        "document_type: topic\n"
        'description: "A test topic document"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n"
        "\n"
        "# Test Topic\n"
        "\n"
        "## Guidance\n\n"
        f"{words}\n\n"
        "## Context\n\nBackground.\n\n"
        "## In Practice\n\nExample.\n\n"
        "## Pitfalls\n\nAvoid this.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )


def _overview_md(word_count: int = 40) -> str:
    """Build a minimal overview with approximately word_count words."""
    words = " ".join(["word"] * word_count)
    return (
        "---\n"
        "document_type: overview\n"
        'description: "Overview of test area"\n'
        "last_updated: 2026-02-17\n"
        "last_validated: 2026-02-17\n"
        "---\n"
        "\n"
        "# Test Area\n"
        "\n"
        "## What This Covers\n\n"
        f"{words}\n\n"
        "## Topics\n\n- test-topic\n\n"
        "## Key Sources\n\n- [Source](https://example.com)\n"
    )


# ── Tests ────────────────────────────────────────────────────────


class TestEstimateTokens:
    """Test the word-count-based token estimation."""

    def test_basic_estimation(self):
        """Token estimate equals round(word_count * 1.3)."""
        doc = parse_document("context/python/error-handling.md", _topic_md(100))
        result = estimate_token_budget([doc])
        word_count = len(doc.raw_content.split())
        expected_tokens = round(word_count * 1.3)
        assert result["total_estimated_tokens"] == expected_tokens

    def test_empty_input(self):
        """No documents yields zero tokens and empty areas."""
        result = estimate_token_budget([])
        assert result["total_estimated_tokens"] == 0
        assert result["over_budget"] is False
        assert result["areas"] == []


class TestAreaGrouping:
    """Test per-area aggregation."""

    def test_multiple_areas(self):
        """Documents are grouped by area extracted from path."""
        doc_a = parse_document("context/python/topic-a.md", _topic_md(50))
        doc_b = parse_document("context/python/topic-b.md", _topic_md(50))
        doc_c = parse_document("context/git/topic-c.md", _topic_md(50))

        result = estimate_token_budget([doc_a, doc_b, doc_c])
        areas = {a["area"]: a for a in result["areas"]}

        assert "python" in areas
        assert "git" in areas
        assert areas["python"]["files"] == 2
        assert areas["git"]["files"] == 1

    def test_area_tokens_sum_to_total(self):
        """Per-area token sums equal the total."""
        doc_a = parse_document("context/python/topic-a.md", _topic_md(80))
        doc_b = parse_document("context/git/topic-b.md", _topic_md(60))

        result = estimate_token_budget([doc_a, doc_b])
        area_sum = sum(a["estimated_tokens"] for a in result["areas"])
        assert area_sum == result["total_estimated_tokens"]


class TestThreshold:
    """Test over-budget detection and issue generation."""

    def test_under_threshold(self):
        """Below threshold: over_budget is False, no issue returned."""
        doc = parse_document("context/python/small.md", _topic_md(10))
        result = estimate_token_budget([doc], warning_threshold=40_000)
        assert result["over_budget"] is False
        assert result.get("issue") is None

    def test_over_threshold(self):
        """Above threshold: over_budget is True, warn issue returned."""
        doc = parse_document("context/python/big.md", _topic_md(10))
        # Use a tiny threshold to trigger over-budget
        result = estimate_token_budget([doc], warning_threshold=1)
        assert result["over_budget"] is True
        issue = result["issue"]
        assert issue["severity"] == "warn"
        assert issue["validator"] == "token_budget"
        assert "threshold" in issue["issue"].lower()

    def test_custom_threshold(self):
        """Custom threshold value is used and reported."""
        doc = parse_document("context/python/topic.md", _topic_md(10))
        result = estimate_token_budget([doc], warning_threshold=99_999)
        assert result["warning_threshold"] == 99_999

    def test_exactly_at_threshold(self):
        """At exactly the threshold: not over budget."""
        doc = parse_document("context/python/topic.md", _topic_md(10))
        total = round(len(doc.raw_content.split()) * 1.3)
        result = estimate_token_budget([doc], warning_threshold=total)
        assert result["over_budget"] is False

    def test_areas_sorted_by_name(self):
        """Areas in output are sorted alphabetically."""
        doc_z = parse_document("context/zsh/topic.md", _topic_md(10))
        doc_a = parse_document("context/aws/topic.md", _topic_md(10))

        result = estimate_token_budget([doc_z, doc_a])
        area_names = [a["area"] for a in result["areas"]]
        assert area_names == sorted(area_names)
