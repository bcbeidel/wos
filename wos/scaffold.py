"""Project scaffolding — create directory structures and template files.

Provides two operations:
  - scaffold_project(): Initialize a new project with context and artifact dirs
  - scaffold_area(): Add a single domain area to an existing project

Never overwrites existing files. Returns a report of what was created/skipped.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional


def scaffold_project(
    root: str,
    areas: List[str],
    purpose: Optional[str] = None,
) -> Dict[str, List[str]]:
    """Initialize a new project with structured context.

    Creates:
      - context/ directory with area subdirectories
      - artifacts/research/ and artifacts/plans/ directories
      - _overview.md in each area

    Returns dict with 'created' and 'skipped' file lists.
    """
    root_path = Path(root)
    created: List[str] = []
    skipped: List[str] = []

    # Create base directories
    for d in [
        root_path / "context",
        root_path / "artifacts" / "research",
        root_path / "artifacts" / "plans",
    ]:
        d.mkdir(parents=True, exist_ok=True)
        created.append(str(d.relative_to(root_path)) + "/")

    # Create each area
    for area_name in areas:
        normalized = normalize_area_name(area_name)
        result = _create_area(root_path, normalized)
        created.extend(result["created"])
        skipped.extend(result["skipped"])

    return {"created": created, "skipped": skipped}


def scaffold_area(
    root: str,
    area_name: str,
    description: Optional[str] = None,
) -> Dict[str, List[str]]:
    """Add a single domain area to an existing project.

    Creates:
      - context/{area}/ directory
      - context/{area}/_overview.md with valid overview frontmatter

    Returns dict with 'created' and 'skipped' file lists.
    """
    root_path = Path(root)
    normalized = normalize_area_name(area_name)
    return _create_area(root_path, normalized, description)


def normalize_area_name(name: str) -> str:
    """Normalize an area name to lowercase-hyphenated format.

    'Python Basics' -> 'python-basics'
    'API Design' -> 'api-design'
    'my_area name' -> 'my-area-name'
    """
    # Replace underscores and spaces with hyphens
    result = re.sub(r"[\s_]+", "-", name.strip())
    # Remove non-alphanumeric except hyphens
    result = re.sub(r"[^a-z0-9-]", "", result.lower())
    # Collapse multiple hyphens
    result = re.sub(r"-+", "-", result).strip("-")
    return result


def _create_area(
    root_path: Path,
    area_name: str,
    description: Optional[str] = None,
) -> Dict[str, List[str]]:
    """Create an area directory with overview file."""
    created: List[str] = []
    skipped: List[str] = []

    area_dir = root_path / "context" / area_name
    area_dir.mkdir(parents=True, exist_ok=True)
    created.append(f"context/{area_name}/")

    overview_path = area_dir / "_overview.md"
    if overview_path.exists():
        skipped.append(f"context/{area_name}/_overview.md")
    else:
        display = _display_name(area_name)
        desc = description or f"{display} concepts and best practices"
        content = _overview_template(display, desc)
        overview_path.write_text(content, encoding="utf-8")
        created.append(f"context/{area_name}/_overview.md")

    return {"created": created, "skipped": skipped}


def _display_name(slug: str) -> str:
    """Convert a hyphenated slug to a display name."""
    return slug.replace("-", " ").title()


def _overview_template(title: str, description: str) -> str:
    """Generate a minimal valid overview document."""
    today = date.today().isoformat()
    return (
        "---\n"
        "document_type: overview\n"
        f'description: "{description}"\n'
        f"last_updated: {today}\n"
        f"last_validated: {today}\n"
        "---\n"
        "\n"
        f"# {title}\n"
        "\n"
        "## What This Covers\n"
        "\n"
        f"This area covers {description.lower()}. "
        "Add more detail about scope and audience here.\n"
        "\n"
        "## Topics\n"
        "\n"
        "<!-- Topics will be listed here as they are added -->\n"
        "\n"
        "## Key Sources\n"
        "\n"
        "<!-- Add authoritative sources for this area -->\n"
    )
