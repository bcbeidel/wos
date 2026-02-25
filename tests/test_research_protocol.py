"""Tests for wos.research_protocol module."""

from __future__ import annotations

from wos.research_protocol import SearchEntry, SearchProtocol


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
