"""Tier 2 pre-screener triggers for LLM-assisted quality assessment.

Each trigger function takes a Document and returns a list of context dicts
that the LLM should evaluate. Empty list means nothing to evaluate.

Dispatch is handled by each document subclass's validate_content() method.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from wos.document_types import Document

TriggerContext = Dict[str, Optional[str]]


def _trigger(
    doc: Document,
    trigger_name: str,
    question: str,
    excerpt: str,
) -> TriggerContext:
    return {
        "file": doc.path,
        "trigger": trigger_name,
        "question": question,
        "excerpt": excerpt,
    }


# ── Shared triggers ──────────────────────────────────────────────


def trigger_description_quality(doc: Document) -> List[TriggerContext]:
    """Flag descriptions that may be low quality for LLM review."""
    desc = doc.frontmatter.description
    triggers: List[TriggerContext] = []

    # Very short descriptions might be placeholders
    if len(desc) < 20:
        triggers.append(
            _trigger(
                doc,
                "description_quality",
                "Is this description informative enough for an agent to "
                "decide whether to read this document?",
                desc,
            )
        )

    return triggers


# ── Topic triggers ───────────────────────────────────────────────


def trigger_in_practice_concreteness(
    doc: Document,
) -> List[TriggerContext]:
    """Flag In Practice sections that may lack concrete examples."""
    section = doc.get_section_content("In Practice", "")
    if not section:
        return []

    # Simple heuristic: no code blocks or bullet lists
    has_code = "```" in section or "    " in section
    has_list = "- " in section or "1. " in section
    if not has_code and not has_list:
        return [
            _trigger(
                doc,
                "in_practice_concreteness",
                "Does this In Practice section contain concrete, "
                "actionable examples?",
                section[:500],
            )
        ]

    return []


def trigger_pitfalls_completeness(
    doc: Document,
) -> List[TriggerContext]:
    """Flag Pitfalls sections that may be incomplete."""
    section = doc.get_section_content("Pitfalls", "")
    if not section:
        return []

    # Very short pitfalls section
    if len(section.split()) < 20:
        return [
            _trigger(
                doc,
                "pitfalls_completeness",
                "Are the listed pitfalls comprehensive enough for "
                "this topic?",
                section[:500],
            )
        ]

    return []


# ── Overview triggers ────────────────────────────────────────────


def trigger_overview_coverage_quality(
    doc: Document,
) -> List[TriggerContext]:
    """Flag overviews where What This Covers may be vague."""
    section = doc.get_section_content("What This Covers", "")
    if not section:
        return []

    if len(section.split()) < 50:
        return [
            _trigger(
                doc,
                "overview_coverage_quality",
                "Does this What This Covers section clearly define "
                "the scope and audience?",
                section[:500],
            )
        ]

    return []


# ── Research triggers ────────────────────────────────────────────


def trigger_question_clarity(doc: Document) -> List[TriggerContext]:
    """Flag research questions that may be unclear."""
    section = doc.get_section_content("Question", "")
    if not section:
        return []

    # No question mark might mean it's not framed as a question
    if "?" not in section:
        return [
            _trigger(
                doc,
                "question_clarity",
                "Is the research question clearly framed as a "
                "specific, answerable question?",
                section[:500],
            )
        ]

    return []


def trigger_finding_groundedness(doc: Document) -> List[TriggerContext]:
    """Flag findings that may not be well-grounded in sources."""
    section = doc.get_section_content("Findings", "")
    if not section:
        return []

    # Simple heuristic: no links or citations in findings
    has_links = "[" in section and "](" in section
    if not has_links and len(section.split()) > 50:
        return [
            _trigger(
                doc,
                "finding_groundedness",
                "Are these findings supported by the cited sources?",
                section[:500],
            )
        ]

    return []


# ── Plan triggers ────────────────────────────────────────────────


def trigger_step_specificity(doc: Document) -> List[TriggerContext]:
    """Flag plan steps that may be too vague."""
    section = doc.get_section_content("Steps", "")
    if not section:
        return []

    # Count numbered items
    steps = [
        line
        for line in section.split("\n")
        if line.strip() and line.strip()[0].isdigit()
    ]
    if len(steps) > 0 and len(section.split()) / len(steps) < 10:
        return [
            _trigger(
                doc,
                "step_specificity",
                "Are these steps specific enough to execute without "
                "ambiguity?",
                section[:500],
            )
        ]

    return []


def trigger_verification_completeness(
    doc: Document,
) -> List[TriggerContext]:
    """Flag verification sections that may be incomplete."""
    section = doc.get_section_content("Verification", "")
    if not section:
        return []

    items = [
        line for line in section.split("\n") if line.strip().startswith("-")
    ]
    if len(items) < 2:
        return [
            _trigger(
                doc,
                "verification_completeness",
                "Are there enough verification criteria to confirm "
                "the plan objectives are met?",
                section[:500],
            )
        ]

    return []


# ── Public API ───────────────────────────────────────────────────


def run_triggers(doc: Document) -> List[TriggerContext]:
    """Run all Tier 2 triggers for a document's type.

    Delegates to doc.validate_content() which uses polymorphic
    dispatch — each document subclass knows its own triggers.
    """
    return doc.validate_content()
