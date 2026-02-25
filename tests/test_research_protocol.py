"""Tests for wos.research_protocol module."""

from __future__ import annotations

from wos.research_protocol import SearchEntry, SearchProtocol, format_protocol


class TestSearchEntry:
    def test_create_entry(self) -> None:
        entry = SearchEntry(
            query="python asyncio",
            source="google",
            date_range="2024-2026",
            results_found=12,
            results_used=3,
        )
        assert entry.query == "python asyncio"
        assert entry.source == "google"
        assert entry.date_range == "2024-2026"
        assert entry.results_found == 12
        assert entry.results_used == 3

    def test_create_entry_no_date_range(self) -> None:
        entry = SearchEntry(
            query="asyncio tutorial",
            source="scholar",
            date_range=None,
            results_found=5,
            results_used=1,
        )
        assert entry.date_range is None


class TestSearchProtocol:
    def test_create_empty_protocol(self) -> None:
        protocol = SearchProtocol(entries=[], not_searched=[])
        assert protocol.entries == []
        assert protocol.not_searched == []

    def test_create_protocol_with_entries(self) -> None:
        entry = SearchEntry("q", "google", None, 10, 2)
        protocol = SearchProtocol(entries=[entry], not_searched=["reddit"])
        assert len(protocol.entries) == 1
        assert protocol.not_searched == ["reddit"]

    def test_default_fields(self) -> None:
        protocol = SearchProtocol()
        assert protocol.entries == []
        assert protocol.not_searched == []


class TestFormatProtocol:
    def test_empty_protocol(self) -> None:
        protocol = SearchProtocol()
        result = format_protocol(protocol)
        assert "No searches recorded" in result

    def test_single_entry(self) -> None:
        entry = SearchEntry("python asyncio", "google", "2024-2026", 12, 3)
        protocol = SearchProtocol(entries=[entry])
        result = format_protocol(protocol)
        assert "python asyncio" in result
        assert "google" in result
        assert "2024-2026" in result
        assert "12" in result
        assert "3" in result
        assert "| Query" in result

    def test_multiple_entries(self) -> None:
        entries = [
            SearchEntry("query one", "google", "2024-2026", 12, 3),
            SearchEntry("query two", "scholar", None, 8, 2),
        ]
        protocol = SearchProtocol(entries=entries)
        result = format_protocol(protocol)
        assert "query one" in result
        assert "query two" in result

    def test_not_searched_included(self) -> None:
        protocol = SearchProtocol(
            entries=[SearchEntry("q", "google", None, 5, 1)],
            not_searched=["Stack Overflow", "Reddit"],
        )
        result = format_protocol(protocol)
        assert "Stack Overflow" in result
        assert "Reddit" in result
        assert "Not searched" in result

    def test_none_date_range_renders_as_dash(self) -> None:
        entry = SearchEntry("q", "google", None, 5, 1)
        protocol = SearchProtocol(entries=[entry])
        result = format_protocol(protocol)
        # None date range should render as em dash
        assert "\u2014" in result
