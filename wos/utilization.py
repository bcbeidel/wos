"""Utilization data layer — track and query document access patterns.

Stores access events as JSONL in .work-os/utilization/log.jsonl.
Each entry records: file path, timestamp, and context (what triggered
the read). Aggregation functions compute per-file stats for
recommendations and dashboards.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# ── Data types ───────────────────────────────────────────────────

class UtilizationEntry:
    """A single access event."""

    __slots__ = ("file", "timestamp", "context")

    def __init__(self, file: str, timestamp: str, context: str = "") -> None:
        self.file = file
        self.timestamp = timestamp
        self.context = context

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "timestamp": self.timestamp,
            "context": self.context,
        }


class FileStats:
    """Aggregated stats for a single file."""

    __slots__ = (
        "file", "read_count", "first_referenced",
        "last_referenced", "unique_contexts",
    )

    def __init__(self, file: str) -> None:
        self.file = file
        self.read_count = 0
        self.first_referenced: Optional[str] = None
        self.last_referenced: Optional[str] = None
        self.unique_contexts: set = set()

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "read_count": self.read_count,
            "first_referenced": self.first_referenced,
            "last_referenced": self.last_referenced,
            "unique_contexts": sorted(self.unique_contexts),
        }


# ── Log path ─────────────────────────────────────────────────────

def _log_path(root: str) -> Path:
    return Path(root) / ".work-os" / "utilization" / "log.jsonl"


# ── Record ───────────────────────────────────────────────────────

def record_reference(
    root: str,
    file_path: str,
    context: str = "",
) -> None:
    """Append a reference event to the utilization log.

    Creates the log file and directories if they don't exist.
    """
    log = _log_path(root)
    log.parent.mkdir(parents=True, exist_ok=True)

    entry = UtilizationEntry(
        file=file_path,
        timestamp=datetime.utcnow().isoformat(timespec="seconds"),
        context=context,
    )
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


# ── Read ─────────────────────────────────────────────────────────

def _read_entries(root: str) -> List[UtilizationEntry]:
    """Read all entries from the log file."""
    log = _log_path(root)
    if not log.exists():
        return []

    entries: List[UtilizationEntry] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            entries.append(UtilizationEntry(
                file=data["file"],
                timestamp=data["timestamp"],
                context=data.get("context", ""),
            ))
        except (json.JSONDecodeError, KeyError):
            continue

    return entries


def read_utilization(root: str) -> Dict[str, FileStats]:
    """Aggregate per-file stats from the utilization log.

    Returns a dict keyed by file path.
    """
    entries = _read_entries(root)
    stats: Dict[str, FileStats] = {}

    for entry in entries:
        if entry.file not in stats:
            stats[entry.file] = FileStats(entry.file)

        s = stats[entry.file]
        s.read_count += 1
        if s.first_referenced is None or entry.timestamp < s.first_referenced:
            s.first_referenced = entry.timestamp
        if s.last_referenced is None or entry.timestamp > s.last_referenced:
            s.last_referenced = entry.timestamp
        if entry.context:
            s.unique_contexts.add(entry.context)

    return stats


def read_utilization_timeseries(
    root: str, file_path: str
) -> List[dict]:
    """Return chronological entries for a specific file."""
    entries = _read_entries(root)
    return [
        e.to_dict() for e in entries
        if e.file == file_path
    ]


# ── Purge ────────────────────────────────────────────────────────

def purge_old_entries(root: str, days: int) -> int:
    """Remove entries older than N days. Returns count of removed entries.

    Rewrites the log file with only recent entries.
    """
    log = _log_path(root)
    if not log.exists():
        return 0

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat(
        timespec="seconds"
    )

    entries = _read_entries(root)
    kept = [e for e in entries if e.timestamp >= cutoff]
    removed = len(entries) - len(kept)

    if removed > 0:
        with open(log, "w", encoding="utf-8") as f:
            for entry in kept:
                f.write(json.dumps(entry.to_dict()) + "\n")

    return removed


# ── Tracking period ──────────────────────────────────────────────

def tracking_start_date(root: str) -> Optional[date]:
    """Return the date of the earliest entry, or None if no data."""
    entries = _read_entries(root)
    if not entries:
        return None

    earliest = min(e.timestamp for e in entries)
    return datetime.fromisoformat(earliest).date()


def tracking_days(root: str) -> int:
    """Return the number of days since the earliest entry."""
    start = tracking_start_date(root)
    if start is None:
        return 0
    return (date.today() - start).days
