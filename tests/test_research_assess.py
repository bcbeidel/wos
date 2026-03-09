"""Tests for wos/research/assess_research.py."""

from __future__ import annotations

import pytest


class TestAssessFile:
    """Tests for assess_file() — single document assessment."""

    def test_assess_minimal_research_doc(self, tmp_path) -> None:
        """Minimal research doc returns expected structural facts."""
        from wos.research.assess_research import assess_file

        doc = tmp_path / "test.md"
        doc.write_text(
            "---\n"
            "name: Test Research\n"
            "description: A test research document\n"
            "type: research\n"
            "sources:\n"
            "  - https://example.com/source-1\n"
            "  - https://example.com/source-2\n"
            "---\n"
            "# Test Research\n"
            "\n"
            "Some content here about the topic.\n"
        )
        result = assess_file(str(doc))

        assert result["file"] == str(doc)
        assert result["exists"] is True
        assert result["frontmatter"]["name"] == "Test Research"
        assert result["frontmatter"]["description"] == "A test research document"
        assert result["frontmatter"]["type"] == "research"
        assert result["frontmatter"]["sources_count"] == 2
        assert result["frontmatter"]["related_count"] == 0
        assert result["content"]["word_count"] > 0
        assert result["content"]["draft_marker_present"] is False
        assert result["sources"]["total"] == 2
        assert "https://example.com/source-1" in result["sources"]["urls"]

    def test_assess_doc_with_draft_marker(self, tmp_path) -> None:
        """Draft marker is detected in content."""
        from wos.research.assess_research import assess_file

        doc = tmp_path / "draft.md"
        doc.write_text(
            "---\n"
            "name: Draft Research\n"
            "description: A draft\n"
            "type: research\n"
            "---\n"
            "<!-- DRAFT -->\n"
            "# Draft Research\n"
            "\n"
            "Work in progress.\n"
        )
        result = assess_file(str(doc))
        assert result["content"]["draft_marker_present"] is True

    def test_assess_doc_with_sections(self, tmp_path) -> None:
        """Section detection finds claims, synthesis, sources, findings headings."""
        from wos.research.assess_research import assess_file

        doc = tmp_path / "full.md"
        doc.write_text(
            "---\n"
            "name: Full Research\n"
            "description: Complete research\n"
            "type: research\n"
            "sources:\n"
            "  - https://example.com/a\n"
            "---\n"
            "# Full Research\n"
            "\n"
            "## Findings\n"
            "\n"
            "Some findings here.\n"
            "\n"
            "## Claims\n"
            "\n"
            "| Claim | Status |\n"
            "| claim 1 | verified |\n"
            "\n"
            "## Sources\n"
            "\n"
            "Source list here.\n"
        )
        result = assess_file(str(doc))
        assert result["content"]["has_sections"]["findings"] is True
        assert result["content"]["has_sections"]["claims"] is True
        assert result["content"]["has_sections"]["sources"] is True
        assert result["content"]["has_sections"]["synthesis"] is False

    def test_assess_doc_with_synthesis_section(self, tmp_path) -> None:
        """Synthesis section is detected."""
        from wos.research.assess_research import assess_file

        doc = tmp_path / "synth.md"
        doc.write_text(
            "---\n"
            "name: Synth Research\n"
            "description: Has synthesis\n"
            "type: research\n"
            "---\n"
            "## Synthesis\n"
            "\n"
            "Synthesized findings.\n"
        )
        result = assess_file(str(doc))
        assert result["content"]["has_sections"]["synthesis"] is True

    def test_assess_nonexistent_file(self) -> None:
        """Non-existent file returns exists=False with null fields."""
        from wos.research.assess_research import assess_file

        result = assess_file("/nonexistent/path/doc.md")
        assert result["file"] == "/nonexistent/path/doc.md"
        assert result["exists"] is False
        assert result["frontmatter"] is None
        assert result["content"] is None
        assert result["sources"] is None

    def test_assess_doc_with_related(self, tmp_path) -> None:
        """Related field count is reported."""
        from wos.research.assess_research import assess_file

        doc = tmp_path / "related.md"
        doc.write_text(
            "---\n"
            "name: Related Research\n"
            "description: Has related docs\n"
            "type: research\n"
            "related:\n"
            "  - docs/research/other.md\n"
            "  - docs/context/topic.md\n"
            "---\n"
            "# Related Research\n"
            "\n"
            "Content.\n"
        )
        result = assess_file(str(doc))
        assert result["frontmatter"]["related_count"] == 2

    def test_assess_doc_with_non_url_sources(self, tmp_path) -> None:
        """Sources that aren't URLs are counted separately."""
        from wos.research.assess_research import assess_file

        doc = tmp_path / "mixed.md"
        doc.write_text(
            "---\n"
            "name: Mixed Sources\n"
            "description: Has URL and non-URL sources\n"
            "type: research\n"
            "sources:\n"
            "  - https://example.com/url-source\n"
            "  - Book: Some Reference Book\n"
            "---\n"
            "# Mixed Sources\n"
            "\n"
            "Content.\n"
        )
        result = assess_file(str(doc))
        assert result["sources"]["total"] == 2
        assert result["sources"]["urls"] == ["https://example.com/url-source"]
        assert result["sources"]["non_url_count"] == 1
