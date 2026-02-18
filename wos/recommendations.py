"""Recommendations engine — data-driven curation suggestions.

Cross-references utilization data against document inventory and health
signals to generate actionable recommendations. Gated by minimum data
thresholds to avoid premature conclusions.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List

from wos.document_types import parse_document
from wos.utilization import FileStats, read_utilization, tracking_days

# ── Thresholds ───────────────────────────────────────────────────

DEFAULT_MIN_READS = 10  # Total reads across all files before generating
DEFAULT_MIN_DAYS = 14  # Days of tracking before generating
STALE_HIGH_USE_READ_THRESHOLD = 50
STALE_HIGH_USE_DAYS_THRESHOLD = 90
NEVER_REFERENCED_DAYS = 14
LOW_UTILIZATION_FACTOR = 0.2  # Below 20% of median = low


# ── Recommendation ───────────────────────────────────────────────

class Recommendation:
    """A single curation recommendation."""

    __slots__ = ("file", "category", "reason", "action")

    def __init__(
        self,
        file: str,
        category: str,
        reason: str,
        action: str,
    ) -> None:
        self.file = file
        self.category = category
        self.reason = reason
        self.action = action

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "category": self.category,
            "reason": self.reason,
            "action": self.action,
        }


# ── Generators ───────────────────────────────────────────────────


def _check_stale_high_use(
    stats: Dict[str, FileStats],
    docs: Dict[str, dict],
) -> List[Recommendation]:
    """Flag documents read frequently but not validated recently."""
    recs: List[Recommendation] = []
    for path, s in stats.items():
        if s.read_count < STALE_HIGH_USE_READ_THRESHOLD:
            continue
        doc_info = docs.get(path)
        if not doc_info:
            continue
        last_validated = doc_info.get("last_validated")
        if last_validated is None:
            continue
        age = (date.today() - last_validated).days
        if age >= STALE_HIGH_USE_DAYS_THRESHOLD:
            recs.append(Recommendation(
                file=path,
                category="stale_high_use",
                reason=(
                    f"Read {s.read_count} times but last validated "
                    f"{age} days ago"
                ),
                action="Prioritize refreshing this document",
            ))
    return recs


def _check_never_referenced(
    all_context_files: List[str],
    stats: Dict[str, FileStats],
    days_tracking: int,
) -> List[Recommendation]:
    """Flag context files with zero reads after sufficient tracking."""
    if days_tracking < NEVER_REFERENCED_DAYS:
        return []

    recs: List[Recommendation] = []
    for path in all_context_files:
        if path not in stats or stats[path].read_count == 0:
            recs.append(Recommendation(
                file=path,
                category="never_referenced",
                reason=(
                    f"Zero reads after {days_tracking} days of tracking"
                ),
                action="Check if this document is linked and discoverable",
            ))
    return recs


def _check_low_utilization(
    stats: Dict[str, FileStats],
    all_context_files: List[str],
) -> List[Recommendation]:
    """Flag files read far below median."""
    if not stats:
        return []

    counts = [
        stats[p].read_count for p in all_context_files
        if p in stats and stats[p].read_count > 0
    ]
    if not counts:
        return []

    counts.sort()
    median = counts[len(counts) // 2]
    threshold = max(1, int(median * LOW_UTILIZATION_FACTOR))

    recs: List[Recommendation] = []
    for path in all_context_files:
        if path in stats and 0 < stats[path].read_count < threshold:
            recs.append(Recommendation(
                file=path,
                category="low_utilization",
                reason=(
                    f"Read {stats[path].read_count} times "
                    f"(median: {median})"
                ),
                action="Consider improving discoverability or relevance",
            ))
    return recs


def _check_hot_cold_areas(
    stats: Dict[str, FileStats],
    all_context_files: List[str],
) -> List[Recommendation]:
    """Flag areas with disproportionately high or low reads."""
    # Group by area
    area_reads: Dict[str, int] = {}
    area_files: Dict[str, int] = {}

    for path in all_context_files:
        parts = path.split("/")
        if len(parts) >= 2:
            area = parts[1]  # context/{area}/...
            area_files[area] = area_files.get(area, 0) + 1
            reads = stats[path].read_count if path in stats else 0
            area_reads[area] = area_reads.get(area, 0) + reads

    if not area_reads:
        return []

    total = sum(area_reads.values())
    if total == 0:
        return []

    avg_per_area = total / len(area_reads)
    recs: List[Recommendation] = []

    for area, reads in area_reads.items():
        if reads > avg_per_area * 3:
            recs.append(Recommendation(
                file=f"context/{area}/",
                category="hot_area",
                reason=(
                    f"{reads} reads across {area_files[area]} files "
                    f"(avg per area: {avg_per_area:.0f})"
                ),
                action="May need more topics or better organization",
            ))
        elif reads < avg_per_area * 0.2 and len(area_reads) > 1:
            recs.append(Recommendation(
                file=f"context/{area}/",
                category="cold_area",
                reason=(
                    f"{reads} reads across {area_files[area]} files "
                    f"(avg per area: {avg_per_area:.0f})"
                ),
                action="May be out of scope or poorly linked",
            ))

    return recs


# ── Main entry point ─────────────────────────────────────────────


def generate_recommendations(
    root: str,
    *,
    min_reads: int = DEFAULT_MIN_READS,
    min_days: int = DEFAULT_MIN_DAYS,
) -> dict:
    """Generate data-driven curation recommendations.

    Returns {"recommendations": [...], "summary": {...}} or
    {"recommendations": [], "skipped": "reason"} if insufficient data.
    """
    days = tracking_days(root)
    stats = read_utilization(root)
    total_reads = sum(s.read_count for s in stats.values())

    if total_reads < min_reads:
        return {
            "recommendations": [],
            "skipped": (
                f"Insufficient data: {total_reads} reads "
                f"(need {min_reads})"
            ),
        }

    if days < min_days:
        return {
            "recommendations": [],
            "skipped": (
                f"Insufficient tracking period: {days} days "
                f"(need {min_days})"
            ),
        }

    # Scan context files
    all_context_files = _scan_context_files(root)
    doc_info = _scan_doc_info(root, all_context_files)

    # Run all recommendation generators
    recs: List[Recommendation] = []
    recs.extend(_check_stale_high_use(stats, doc_info))
    recs.extend(_check_never_referenced(all_context_files, stats, days))
    recs.extend(_check_low_utilization(stats, all_context_files))
    recs.extend(_check_hot_cold_areas(stats, all_context_files))

    return {
        "recommendations": [r.to_dict() for r in recs],
        "summary": {
            "total_reads": total_reads,
            "tracking_days": days,
            "files_tracked": len(stats),
            "context_files": len(all_context_files),
            "recommendation_count": len(recs),
        },
    }


# ── Helpers ──────────────────────────────────────────────────────


def _scan_context_files(root: str) -> List[str]:
    """Find all .md files under context/."""
    context_dir = Path(root) / "context"
    if not context_dir.is_dir():
        return []

    files: List[str] = []
    for md_file in context_dir.rglob("*.md"):
        files.append(str(md_file.relative_to(root)))
    return sorted(files)


def _scan_doc_info(
    root: str, files: List[str]
) -> Dict[str, dict]:
    """Parse documents and extract info needed for recommendations."""
    root_path = Path(root)
    info: Dict[str, dict] = {}

    for rel_path in files:
        full_path = root_path / rel_path
        if not full_path.is_file():
            continue
        try:
            content = full_path.read_text(encoding="utf-8")
            doc = parse_document(rel_path, content)
            entry: dict = {"document_type": doc.document_type.value}
            fm = doc.frontmatter
            if hasattr(fm, "last_validated") and fm.last_validated:
                entry["last_validated"] = fm.last_validated
            info[rel_path] = entry
        except Exception:
            continue

    return info
