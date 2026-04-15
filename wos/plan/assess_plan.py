"""Plan document structural assessment.

Reports observable facts about plan documents — status, task completion,
section presence. The model infers execution state and next actions from
these facts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from wos.document import PlanDocument, parse_document

_PLAN_SECTIONS = {
    "goal": "goal",
    "scope": "scope",
    "approach": "approach",
    "file_changes": "file changes",
    "tasks": "tasks",
    "validation": "validation",
}


def _detect_sections(doc: PlanDocument) -> Dict[str, bool]:
    """Check for presence of 6 required plan sections by heading text."""
    found = {key: doc.has_section(keyword) for key, keyword in _PLAN_SECTIONS.items()}
    found["all_present"] = all(found.values())
    return found


def assess_file(path: str) -> dict:
    """Assess structural facts of a single plan document.

    Args:
        path: Absolute or relative path to a plan markdown file.

    Returns:
        Dict with keys: file, exists, frontmatter, sections, tasks,
        readiness. If file doesn't exist, all values except file and
        exists are None.
    """
    if not os.path.isfile(path):
        return {
            "file": path,
            "exists": False,
            "frontmatter": None,
            "sections": None,
            "tasks": None,
            "readiness": None,
        }

    text = Path(path).read_text(encoding="utf-8")
    doc = parse_document(path, text)

    sections = _detect_sections(doc)
    tasks = doc.tasks if isinstance(doc, PlanDocument) else []

    completed = sum(1 for t in tasks if t["completed"])
    pending = len(tasks) - completed

    executable_statuses = {"approved", "executing"}
    status_ok = doc.status in executable_statuses
    issues: List[str] = []
    if doc.status and doc.status not in executable_statuses:
        issues.append(f"Status is '{doc.status}' — not executable")
    if doc.status is None:
        issues.append("No status field — legacy plan")
        status_ok = True  # allow with warning
    if not sections["all_present"]:
        missing = [
            k for k, v in sections.items()
            if k != "all_present" and not v
        ]
        issues.append(f"Missing sections: {', '.join(missing)}")

    return {
        "file": path,
        "exists": True,
        "frontmatter": {
            "name": doc.name,
            "status": doc.status,
            "type": doc.type,
        },
        "sections": sections,
        "tasks": {
            "total": len(tasks),
            "completed": completed,
            "pending": pending,
            "items": tasks,
        },
        "readiness": {
            "status_ok": status_ok,
            "sections_complete": sections["all_present"],
            "has_pending_tasks": pending > 0,
            "issues": issues,
        },
    }


def scan_plans(root: str, subdir: str = "") -> dict:
    """Find plans with status: executing in the project.

    Uses the discovery module to find all type: plan documents with
    status: executing. If subdir is provided, restricts to that
    subdirectory.

    Args:
        root: Project root directory.
        subdir: Optional subdirectory to restrict scan (default: full tree).

    Returns:
        Dict with keys: directory, plans. Each plan has: file, name,
        status, total_tasks, completed_tasks, pending_tasks.
    """
    from wos.discovery import filter_documents

    label, plan_docs = filter_documents(
        Path(root), "plan", subdir=subdir, status="executing"
    )
    plans = []
    for doc in plan_docs:
        tasks = doc.tasks if isinstance(doc, PlanDocument) else []
        completed = sum(1 for t in tasks if t["completed"])
        plans.append({
            "file": os.path.join(root, doc.path),
            "name": doc.name,
            "status": doc.status,
            "total_tasks": len(tasks),
            "completed_tasks": completed,
            "pending_tasks": len(tasks) - completed,
        })
    return {"directory": label, "plans": plans}
