"""Plan document structural assessment.

Reports observable facts about plan documents — status, task completion,
section presence, file-boundary analysis. The model infers execution
state and next actions from these facts.
"""

from __future__ import annotations

import re
from typing import Dict, List

_TASK_RE = re.compile(
    r"^- \[([ xX])\] "          # checkbox at line start (not indented)
    r"(?:Task \d+:\s*)?"        # optional "Task N: " prefix
    r"(.+?)"                    # title (non-greedy)
    r"(?:\s*<!--\s*sha:(\w+)\s*-->)?"  # optional SHA annotation
    r"\s*$",
)


def _parse_tasks(content: str) -> List[dict]:
    """Extract top-level checkbox items from plan content.

    Parses ``- [ ] Task N: title`` and ``- [x] Task N: title <!-- sha:abc -->``
    patterns. Indented checkboxes (sub-steps) are ignored.

    Returns:
        List of dicts with keys: index, title, completed, sha.
    """
    tasks: List[dict] = []
    index = 0
    for line in content.split("\n"):
        match = _TASK_RE.match(line)
        if not match:
            continue
        index += 1
        check, title, sha = match.groups()
        tasks.append({
            "index": index,
            "title": title.strip(),
            "completed": check.lower() == "x",
            "sha": sha,
        })
    return tasks


_PLAN_SECTIONS = {
    "goal": "goal",
    "scope": "scope",
    "approach": "approach",
    "file_changes": "file changes",
    "tasks": "tasks",
    "validation": "validation",
}


def _detect_sections(content: str) -> Dict[str, bool]:
    """Check for presence of 6 required plan sections by heading text.

    Returns:
        Dict mapping section keys to bool, plus 'all_present' summary.
    """
    found: Dict[str, bool] = {key: False for key in _PLAN_SECTIONS}
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading_text = stripped.lstrip("#").strip().lower()
        for key, keyword in _PLAN_SECTIONS.items():
            if keyword in heading_text:
                found[key] = True
    found["all_present"] = all(
        v for k, v in found.items() if k != "all_present"
    )
    return found


_FILE_CHANGE_RE = re.compile(
    r"^-\s*(?:Create|Modify|Delete|Test):\s*`?([^`\s]+?)(?::\d[\d\-]*)?`?\s*$",
    re.IGNORECASE,
)


def _extract_file_changes(content: str) -> List[str]:
    """Extract file paths from the File Changes section.

    Parses lines like ``- Create: `path/to/file.py` `` between
    the File Changes heading and the next heading.

    Returns:
        List of file path strings.
    """
    files: List[str] = []
    in_section = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            if "file changes" in heading:
                in_section = True
                continue
            elif in_section:
                break  # hit next section
        if not in_section:
            continue
        match = _FILE_CHANGE_RE.match(stripped)
        if match:
            files.append(match.group(1))
    return files
