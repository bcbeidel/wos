"""Tests for wos.utilization — utilization data layer."""

from __future__ import annotations

import json

from wos.utilization import (
    purge_old_entries,
    read_utilization,
    read_utilization_timeseries,
    record_reference,
    tracking_days,
    tracking_start_date,
)


class TestRecordReference:
    def test_creates_log_file(self, tmp_path) -> None:
        record_reference(str(tmp_path), "context/test/topic.md")
        log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
        assert log.exists()

    def test_appends_valid_jsonl(self, tmp_path) -> None:
        record_reference(str(tmp_path), "context/test/a.md")
        record_reference(str(tmp_path), "context/test/b.md")
        log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
        lines = log.read_text().strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert "file" in data
            assert "timestamp" in data

    def test_includes_context(self, tmp_path) -> None:
        record_reference(
            str(tmp_path), "context/test/topic.md", context="agent-read"
        )
        log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
        data = json.loads(log.read_text().strip())
        assert data["context"] == "agent-read"


class TestReadUtilization:
    def test_empty_log(self, tmp_path) -> None:
        stats = read_utilization(str(tmp_path))
        assert stats == {}

    def test_counts_reads(self, tmp_path) -> None:
        root = str(tmp_path)
        for _ in range(5):
            record_reference(root, "context/test/topic.md")
        record_reference(root, "context/test/other.md")

        stats = read_utilization(root)
        assert stats["context/test/topic.md"].read_count == 5
        assert stats["context/test/other.md"].read_count == 1

    def test_tracks_first_and_last_referenced(self, tmp_path) -> None:
        root = str(tmp_path)
        # Write entries with known timestamps
        log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
        log.parent.mkdir(parents=True)
        entries = [
            {"file": "context/a.md", "timestamp": "2026-01-01T00:00:00"},
            {"file": "context/a.md", "timestamp": "2026-02-15T00:00:00"},
            {"file": "context/a.md", "timestamp": "2026-01-15T00:00:00"},
        ]
        log.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )

        stats = read_utilization(root)
        s = stats["context/a.md"]
        assert s.first_referenced == "2026-01-01T00:00:00"
        assert s.last_referenced == "2026-02-15T00:00:00"

    def test_tracks_unique_contexts(self, tmp_path) -> None:
        root = str(tmp_path)
        record_reference(root, "context/a.md", context="agent")
        record_reference(root, "context/a.md", context="agent")
        record_reference(root, "context/a.md", context="human")

        stats = read_utilization(root)
        assert stats["context/a.md"].unique_contexts == {"agent", "human"}

    def test_handles_malformed_lines(self, tmp_path) -> None:
        log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
        log.parent.mkdir(parents=True)
        log.write_text(
            'not json\n'
            '{"file": "a.md", "timestamp": "2026-01-01T00:00:00"}\n'
            '\n'
        )
        stats = read_utilization(str(tmp_path))
        assert len(stats) == 1


class TestReadUtilizationTimeseries:
    def test_filters_by_file(self, tmp_path) -> None:
        root = str(tmp_path)
        record_reference(root, "context/a.md")
        record_reference(root, "context/b.md")
        record_reference(root, "context/a.md")

        ts = read_utilization_timeseries(root, "context/a.md")
        assert len(ts) == 2
        assert all(e["file"] == "context/a.md" for e in ts)


class TestPurgeOldEntries:
    def test_removes_old_entries(self, tmp_path) -> None:
        log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
        log.parent.mkdir(parents=True)
        entries = [
            {"file": "old.md", "timestamp": "2025-01-01T00:00:00"},
            {"file": "new.md", "timestamp": "2026-02-17T00:00:00"},
        ]
        log.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )

        removed = purge_old_entries(str(tmp_path), days=30)
        assert removed == 1

        stats = read_utilization(str(tmp_path))
        assert "old.md" not in stats
        assert "new.md" in stats

    def test_empty_log(self, tmp_path) -> None:
        removed = purge_old_entries(str(tmp_path), days=30)
        assert removed == 0

    def test_preserves_recent_entries(self, tmp_path) -> None:
        root = str(tmp_path)
        record_reference(root, "context/recent.md")
        removed = purge_old_entries(root, days=1)
        assert removed == 0
        stats = read_utilization(root)
        assert "context/recent.md" in stats


class TestTrackingPeriod:
    def test_no_data(self, tmp_path) -> None:
        assert tracking_start_date(str(tmp_path)) is None
        assert tracking_days(str(tmp_path)) == 0

    def test_with_data(self, tmp_path) -> None:
        log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
        log.parent.mkdir(parents=True)
        log.write_text(
            '{"file": "a.md", "timestamp": "2026-02-01T00:00:00"}\n'
        )
        start = tracking_start_date(str(tmp_path))
        assert start is not None
        assert start.year == 2026
        assert start.month == 2
