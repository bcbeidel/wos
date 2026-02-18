"""Tests for wos.recommendations — data-driven curation suggestions."""

from __future__ import annotations

import json
from datetime import date, timedelta

from wos.recommendations import (
    generate_recommendations,
)

# ── Helpers ──────────────────────────────────────────────────────

TODAY = date.today().isoformat()


def _setup_log(tmp_path, entries):
    """Write utilization log entries."""
    log = tmp_path / ".work-os" / "utilization" / "log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _setup_topic(tmp_path, rel_path, *, last_validated=None):
    """Create a minimal valid topic file."""
    if last_validated is None:
        last_validated = TODAY
    full = tmp_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(
        "---\n"
        "document_type: topic\n"
        f'description: "A test topic for recommendations"\n'
        f"last_updated: {TODAY}\n"
        f"last_validated: {last_validated}\n"
        "sources:\n"
        '  - url: "https://example.com"\n'
        '    title: "Example"\n'
        "---\n\n"
        "# Test Topic\n\n"
        "## Guidance\n\nContent.\n\n"
        "## Context\n\nContent.\n\n"
        "## In Practice\n\nContent.\n\n"
        "## Pitfalls\n\nContent.\n\n"
        "## Go Deeper\n\n- [Link](https://example.com)\n"
    )


def _old_timestamp(days_ago):
    """Generate a timestamp N days ago."""
    d = date.today() - timedelta(days=days_ago)
    return f"{d.isoformat()}T00:00:00"


# ── Gating ───────────────────────────────────────────────────────


class TestGating:
    def test_insufficient_reads(self, tmp_path) -> None:
        _setup_log(tmp_path, [
            {"file": "context/a/t.md", "timestamp": _old_timestamp(30)},
        ])
        result = generate_recommendations(str(tmp_path))
        assert "skipped" in result
        assert result["recommendations"] == []

    def test_insufficient_days(self, tmp_path) -> None:
        # Many reads but all today
        entries = [
            {"file": f"context/a/t{i}.md", "timestamp": TODAY + "T00:00:00"}
            for i in range(20)
        ]
        _setup_log(tmp_path, entries)
        result = generate_recommendations(str(tmp_path))
        assert "skipped" in result

    def test_custom_thresholds(self, tmp_path) -> None:
        _setup_log(tmp_path, [
            {"file": "context/a/t.md", "timestamp": _old_timestamp(5)},
            {"file": "context/a/t.md", "timestamp": _old_timestamp(4)},
            {"file": "context/a/t.md", "timestamp": _old_timestamp(3)},
        ])
        _setup_topic(tmp_path, "context/a/t.md")
        result = generate_recommendations(
            str(tmp_path), min_reads=2, min_days=3
        )
        assert "skipped" not in result


# ── Stale high use ───────────────────────────────────────────────


class TestStaleHighUse:
    def test_fires_when_stale_and_high_reads(self, tmp_path) -> None:
        old_date = (date.today() - timedelta(days=100)).isoformat()
        _setup_topic(
            tmp_path, "context/test/topic.md", last_validated=old_date
        )
        entries = [
            {
                "file": "context/test/topic.md",
                "timestamp": _old_timestamp(i),
            }
            for i in range(55)
        ]
        _setup_log(tmp_path, entries)

        result = generate_recommendations(
            str(tmp_path), min_reads=10, min_days=1
        )
        cats = [r["category"] for r in result["recommendations"]]
        assert "stale_high_use" in cats

    def test_does_not_fire_with_few_reads(self, tmp_path) -> None:
        old_date = (date.today() - timedelta(days=100)).isoformat()
        _setup_topic(
            tmp_path, "context/test/topic.md", last_validated=old_date
        )
        entries = [
            {
                "file": "context/test/topic.md",
                "timestamp": _old_timestamp(i),
            }
            for i in range(15)
        ]
        _setup_log(tmp_path, entries)

        result = generate_recommendations(
            str(tmp_path), min_reads=10, min_days=1
        )
        cats = [r["category"] for r in result["recommendations"]]
        assert "stale_high_use" not in cats


# ── Never referenced ─────────────────────────────────────────────


class TestNeverReferenced:
    def test_fires_for_unread_file(self, tmp_path) -> None:
        _setup_topic(tmp_path, "context/test/unread.md")
        _setup_topic(tmp_path, "context/test/read.md")
        entries = [
            {
                "file": "context/test/read.md",
                "timestamp": _old_timestamp(i),
            }
            for i in range(15)
        ]
        _setup_log(tmp_path, entries)

        result = generate_recommendations(
            str(tmp_path), min_reads=10, min_days=1
        )
        never = [
            r for r in result["recommendations"]
            if r["category"] == "never_referenced"
        ]
        files = [r["file"] for r in never]
        assert "context/test/unread.md" in files

    def test_does_not_fire_before_threshold(self, tmp_path) -> None:
        _setup_topic(tmp_path, "context/test/unread.md")
        entries = [
            {
                "file": "context/test/other.md",
                "timestamp": _old_timestamp(5),
            }
            for _ in range(15)
        ]
        _setup_log(tmp_path, entries)

        # Only 5 days of tracking — below NEVER_REFERENCED_DAYS (14)
        result = generate_recommendations(
            str(tmp_path), min_reads=10, min_days=1
        )
        never = [
            r for r in result["recommendations"]
            if r["category"] == "never_referenced"
        ]
        assert len(never) == 0


# ── Summary ──────────────────────────────────────────────────────


class TestSummary:
    def test_summary_fields(self, tmp_path) -> None:
        _setup_topic(tmp_path, "context/test/topic.md")
        entries = [
            {
                "file": "context/test/topic.md",
                "timestamp": _old_timestamp(i),
            }
            for i in range(20)
        ]
        _setup_log(tmp_path, entries)

        result = generate_recommendations(
            str(tmp_path), min_reads=10, min_days=1
        )
        assert "summary" in result
        s = result["summary"]
        assert s["total_reads"] == 20
        assert s["files_tracked"] == 1
        assert s["context_files"] == 1
