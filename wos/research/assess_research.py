"""Research document structural assessment.

Reports observable facts about research documents — word count, draft
markers, section presence, source listing. The model infers phase and
next actions from these facts.
"""

from __future__ import annotations

import os
from typing import Dict, List

from wos.document import parse_document


def assess_file(path: str) -> dict:
    """Assess structural facts of a single research document.

    Args:
        path: Absolute or relative path to a markdown file.

    Returns:
        Dict with keys: file, exists, frontmatter, content, sources.
        If the file doesn't exist, frontmatter/content/sources are None.
    """
    if not os.path.isfile(path):
        return {
            "file": path,
            "exists": False,
            "frontmatter": None,
            "content": None,
            "sources": None,
        }

    text = _read_file(path)
    doc = parse_document(path, text)

    urls, non_url_count = _classify_sources(doc.sources)
    sections = _detect_sections(doc.content)
    word_count = len(doc.content.split())

    return {
        "file": path,
        "exists": True,
        "frontmatter": {
            "name": doc.name,
            "description": doc.description,
            "type": doc.type,
            "sources_count": len(doc.sources),
            "related_count": len(doc.related),
        },
        "content": {
            "word_count": word_count,
            "draft_marker_present": "<!-- DRAFT -->" in doc.content,
            "has_sections": sections,
        },
        "sources": {
            "total": len(doc.sources),
            "urls": urls,
            "non_url_count": non_url_count,
        },
    }


def _read_file(path: str) -> str:
    """Read file content as UTF-8 text."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _classify_sources(sources: List[str]) -> tuple:
    """Split sources into URLs and non-URLs.

    Returns:
        Tuple of (url_list, non_url_count).
    """
    urls: List[str] = []
    non_url_count = 0
    for source in sources:
        if source.startswith("http://") or source.startswith("https://"):
            urls.append(source)
        else:
            non_url_count += 1
    return urls, non_url_count


_SECTION_KEYWORDS = {
    "claims": "claims",
    "synthesis": "synthesis",
    "sources": "sources",
    "findings": "findings",
}


def _detect_sections(content: str) -> Dict[str, bool]:
    """Detect presence of key sections by heading text.

    Looks for markdown headings containing known keywords.
    """
    found = {key: False for key in _SECTION_KEYWORDS}
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading_text = stripped.lstrip("#").strip().lower()
        for key, keyword in _SECTION_KEYWORDS.items():
            if keyword in heading_text:
                found[key] = True
    return found
