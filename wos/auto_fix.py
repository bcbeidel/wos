"""Auto-fix engine — apply safe corrections to health issues.

Each fix function takes raw markdown content and an issue dict (from validators),
returns (fixed_content, description) or None if no fix is possible.

AUTO_FIXES is the dispatch table keyed by validator name. Adding a new
auto-fixable validator means adding an entry here.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Callable, Dict, List, Optional, Tuple

import yaml

from wos.document_types import (
    SECTIONS,
    DocumentType,
    PlanStatus,
    ValidationIssue,
    parse_document,
)

# ── Types ────────────────────────────────────────────────────────

FixResult = Tuple[str, str]  # (fixed_content, description)
FixFn = Callable[[str, str, ValidationIssue], Optional[FixResult]]

# path, content, issue -> optional (new_content, description)


# ── Fix functions ────────────────────────────────────────────────


def fix_section_ordering(
    path: str, content: str, issue: ValidationIssue
) -> Optional[FixResult]:
    """Reorder H2 sections to match canonical order for the document type."""
    try:
        doc = parse_document(path, content)
    except Exception:
        return None

    specs = SECTIONS.get(doc.document_type)
    if not specs:
        return None

    canonical_order = [s.name for s in specs]

    # Split content into frontmatter + title + sections
    fm_match = re.match(r"\A---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if not fm_match:
        return None

    body = content[fm_match.end():]

    # Extract title (everything before first H2)
    first_h2 = re.search(r"^##\s+", body, re.MULTILINE)
    if not first_h2:
        return None

    title_part = body[:first_h2.start()]

    # Parse sections by H2 headings
    h2_re = re.compile(r"^(##\s+.+)$", re.MULTILINE)
    h2_matches = list(h2_re.finditer(body))
    if len(h2_matches) < 2:
        return None

    sections: List[Tuple[str, str]] = []
    for i, m in enumerate(h2_matches):
        name = m.group(1).replace("## ", "").strip()
        start = m.start()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(body)
        sections.append((name, body[start:end]))

    # Sort: canonical sections first (in order), then non-canonical (preserve order)
    canonical_set = set(canonical_order)
    canonical_sections = []
    extra_sections = []
    for name, text in sections:
        if name in canonical_set:
            canonical_sections.append((name, text))
        else:
            extra_sections.append((name, text))

    # Sort canonical sections by their position in the spec
    canonical_sections.sort(
        key=lambda x: canonical_order.index(x[0])
    )

    reordered = canonical_sections + extra_sections
    reordered_body = title_part + "".join(text for _, text in reordered)

    fixed = content[:fm_match.end()] + reordered_body

    # Normalize trailing newline
    if not fixed.endswith("\n"):
        fixed += "\n"

    # Validate the fix
    try:
        parse_document(path, fixed)
    except Exception:
        return None

    return (fixed, "Reordered sections to canonical order")


def fix_missing_sections(
    path: str, content: str, issue: ValidationIssue
) -> Optional[FixResult]:
    """Add missing required sections with TODO placeholders."""
    section_name = issue.section
    if not section_name:
        return None

    try:
        doc = parse_document(path, content)
    except Exception:
        return None

    specs = SECTIONS.get(doc.document_type)
    if not specs:
        return None

    # Find where to insert: after the section that precedes it in canonical order
    canonical_order = [s.name for s in specs]
    if section_name not in canonical_order:
        return None

    target_idx = canonical_order.index(section_name)

    # Find the insertion point in the body
    lower = section_name.lower()
    new_section = f"\n## {section_name}\n\n<!-- TODO: Add {lower} content -->\n"

    if target_idx == 0:
        # Insert after title (first H1)
        h1_match = re.search(r"^#\s+.+$", content, re.MULTILINE)
        if not h1_match:
            return None
        insert_pos = h1_match.end()
        fixed = content[:insert_pos] + "\n" + new_section + content[insert_pos:]
    else:
        # Insert after the preceding canonical section (or at the end)
        preceding = None
        for i in range(target_idx - 1, -1, -1):
            if canonical_order[i] in doc.sections:
                preceding = canonical_order[i]
                break

        if preceding:
            # Find the end of the preceding section
            pattern = rf"^##\s+{re.escape(preceding)}\b"
            match = re.search(pattern, content, re.MULTILINE)
            if not match:
                return None

            # Find the next H2 after this one
            after_match = content[match.end():]
            next_h2 = re.search(r"^##\s+", after_match, re.MULTILINE)
            if next_h2:
                insert_pos = match.end() + next_h2.start()
            else:
                insert_pos = len(content.rstrip()) + 1
            fixed = content[:insert_pos] + new_section + "\n" + content[insert_pos:]
        else:
            # No preceding section exists — insert after title
            h1_match = re.search(r"^#\s+.+$", content, re.MULTILINE)
            if not h1_match:
                return None
            insert_pos = h1_match.end()
            fixed = content[:insert_pos] + "\n" + new_section + content[insert_pos:]

    # Validate the fix
    try:
        parse_document(path, fixed)
    except Exception:
        return None

    return (fixed, f"Added missing section: ## {section_name}")


def fix_missing_last_updated(
    path: str, content: str, issue: ValidationIssue
) -> Optional[FixResult]:
    """Set last_updated to today if missing or invalid."""
    today = date.today().isoformat()

    fm_match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)
    try:
        fm_dict = yaml.safe_load(fm_text)
    except Exception:
        return None

    if not isinstance(fm_dict, dict):
        return None

    if "last_updated" in fm_dict and fm_dict["last_updated"]:
        return None  # Already has a valid value

    fm_dict["last_updated"] = today
    new_fm = yaml.dump(fm_dict, default_flow_style=False, sort_keys=False).rstrip()
    fixed = f"---\n{new_fm}\n---\n{content[fm_match.end():]}"

    try:
        parse_document(path, fixed)
    except Exception:
        return None

    return (fixed, f"Set last_updated to {today}")


# ── Lifecycle transitions ────────────────────────────────────────

# Valid transitions: from_status -> set of allowed to_statuses
VALID_TRANSITIONS: Dict[PlanStatus, List[PlanStatus]] = {
    PlanStatus.DRAFT: [PlanStatus.ACTIVE, PlanStatus.ABANDONED],
    PlanStatus.ACTIVE: [PlanStatus.COMPLETE, PlanStatus.ABANDONED],
    PlanStatus.COMPLETE: [PlanStatus.ACTIVE],  # reopen
    PlanStatus.ABANDONED: [PlanStatus.DRAFT],  # resurrect
}


def transition_status(
    path: str,
    content: str,
    new_status: PlanStatus,
) -> Optional[FixResult]:
    """Update a plan's status field and last_updated date.

    Returns None if the transition is invalid.
    """
    try:
        doc = parse_document(path, content)
    except Exception:
        return None

    if doc.document_type != DocumentType.PLAN:
        return None

    current = doc.frontmatter.status
    if isinstance(current, str):
        current = PlanStatus(current)

    allowed = VALID_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        return None

    today = date.today().isoformat()

    # Update frontmatter via regex replacement
    fixed = content

    # Replace status
    fixed = re.sub(
        r"^status:\s*\S+",
        f"status: {new_status.value}",
        fixed,
        count=1,
        flags=re.MULTILINE,
    )

    # Replace last_updated
    fixed = re.sub(
        r"^last_updated:\s*\S+",
        f"last_updated: {today}",
        fixed,
        count=1,
        flags=re.MULTILINE,
    )

    try:
        parse_document(path, fixed)
    except Exception:
        return None

    return (
        fixed,
        f"Transitioned status: {current.value} -> {new_status.value}",
    )


# ── Cleanup ──────────────────────────────────────────────────────


def find_unparseable_files(
    root: str,
    files: List[str],
) -> List[dict]:
    """Identify markdown files that fail parse_document().

    Returns list of dicts with keys: file, error.
    """
    from pathlib import Path

    results: List[dict] = []
    root_path = Path(root)

    for rel_path in files:
        full_path = root_path / rel_path
        if not full_path.is_file():
            results.append({"file": rel_path, "error": "File not found"})
            continue

        try:
            content = full_path.read_text(encoding="utf-8")
            parse_document(rel_path, content)
        except Exception as e:
            results.append({"file": rel_path, "error": str(e)})

    return results


# ── Dispatch table ───────────────────────────────────────────────

AUTO_FIXES: Dict[str, FixFn] = {
    "check_section_ordering": fix_section_ordering,
    "check_section_presence": fix_missing_sections,
}


def apply_auto_fixes(
    path: str,
    content: str,
    issues: List[ValidationIssue],
    *,
    dry_run: bool = False,
) -> List[dict]:
    """Apply all available auto-fixes for the given issues.

    Returns a list of results: [{file, fix, description, applied}].
    Each result indicates what was (or would be) fixed.
    """
    results: List[dict] = []
    current = content

    for issue in issues:
        fix_fn = AUTO_FIXES.get(issue.validator)
        if not fix_fn:
            continue

        result = fix_fn(path, current, issue)
        if result is None:
            continue

        fixed_content, description = result
        entry = {
            "file": path,
            "fix": issue.validator,
            "description": description,
            "applied": not dry_run,
        }
        results.append(entry)

        if not dry_run:
            current = fixed_content

    return results


def get_fixed_content(
    path: str,
    content: str,
    issues: List[ValidationIssue],
) -> Optional[str]:
    """Apply all auto-fixes and return the final content, or None if no fixes."""
    current = content
    any_fixed = False

    for issue in issues:
        fix_fn = AUTO_FIXES.get(issue.validator)
        if not fix_fn:
            continue

        result = fix_fn(path, current, issue)
        if result is not None:
            current, _ = result
            any_fixed = True

    return current if any_fixed else None
