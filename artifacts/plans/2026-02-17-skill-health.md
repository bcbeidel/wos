---
document_type: plan
description: "Build the health skill with type-dispatched Tier 1 validators, Tier 2 LLM triggers, and Tier 3 human review queue across all four document types"
last_updated: 2026-02-17
status: draft
related:
  - 2026-02-17-document-type-models.md
  - ../research/2026-02-16-document-type-data-models.md
  - ../research/2026-02-17-skills-architecture-design.md
---

# Build Health Skill

## Objective

A `/dewey:health` skill exists that validates knowledge base quality across
all four document types. It is read-only — it reports but does not modify.
Validators are type-dispatched via `VALIDATORS_BY_TYPE` and
`TIER2_TRIGGERS_BY_TYPE` dispatch tables. Adding a new document type requires
only adding entries to these tables, not changing validator code.

The skill supports five workflows: check (T1), audit (T1+T2), review
(T1+T2+T3), coverage analysis, and freshness reporting.

## Context

- Skills architecture: `artifacts/research/2026-02-17-skills-architecture-design.md` §3.2
- Validator dispatch: `artifacts/research/2026-02-16-document-type-data-models.md` §8-9
- Depends on document type models (parse, validate, dispatch)
- Health is read-only; maintain handles write actions
- CI-friendly: `health-check` exits non-zero on `severity: fail`

## Steps

1. Create `skills/health/SKILL.md` with skill description, conversational
   triggers ("check health", "validate", "audit", "review", "coverage",
   "freshness"), and routing by keyword in arguments

2. Implement `scripts/validators.py` — per-file validators, each function
   takes a `Document` and returns `list[dict]`:
   - Shared validators (all types): `check_description_quality`,
     `check_title_heading`, `check_heading_hierarchy`, `check_size_bounds`,
     `check_placeholder_comments`, `check_date_fields`,
     `check_section_presence`, `check_section_ordering`,
     `check_directory_placement`
   - Topic-specific: `check_source_diversity`, `check_citation_grounding`,
     `check_go_deeper_links`, `check_readability`, `check_last_validated`
   - Overview-specific: `check_overview_topic_sync`, `check_topics_table_format`,
     `check_what_this_covers_length`, `check_readability`, `check_last_validated`
   - Research-specific: `check_source_diversity`, `check_citation_grounding`,
     `check_question_nonempty`, `check_date_prefix_matches`
   - Plan-specific: `check_date_prefix_matches`

3. Implement `scripts/cross_validators.py` — validators that need the full
   file set: `check_link_graph`, `check_duplicate_content`,
   `check_naming_conventions`, `check_overview_topic_sync`,
   `check_manifest_sync`

4. Implement `scripts/tier2_triggers.py` — pre-screener functions that return
   context dicts for LLM evaluation:
   - Shared: `trigger_description_quality`
   - Topic: `trigger_why_quality`, `trigger_in_practice_concreteness`,
     `trigger_source_drift`, `trigger_source_authority`,
     `trigger_pitfalls_completeness`
   - Overview: `trigger_overview_coverage_quality`,
     `trigger_overview_navigation_quality`
   - Research: `trigger_question_clarity`, `trigger_finding_groundedness`,
     `trigger_implication_relevance`
   - Plan: `trigger_step_specificity`, `trigger_verification_completeness`,
     `trigger_objective_clarity`, `trigger_context_sufficiency`

5. Implement `scripts/check_knowledge_base.py` — CLI entry point:
   - Parse all documents via `parse_document()`
   - Run shared + type-specific validators per file
   - Run cross-validators
   - Optionally run Tier 2 triggers (`--tier2` flag)
   - Output JSON report: `{"files_checked": N, "issues": [...], "triggers": [...]}`
   - Exit code: 0 if no `severity: fail`, 1 otherwise

6. Create workflows:
   - `health-check.md`: run T1, format results, suggest fixes
   - `health-audit.md`: run T1+T2, Claude evaluates triggered items
   - `health-review.md`: run T1+T2+T3, surface human decision queue
   - `health-coverage.md`: compare manifest against expected coverage
   - `health-freshness.md`: group documents by `last_validated` staleness

7. Write tests: each validator has positive and negative test cases,
   dispatch tables route correctly per type, CLI produces valid JSON,
   cross-validators detect real issues

## Verification

- `python3 scripts/check_knowledge_base.py --knowledge-base-root /path/to/kb`
  produces valid JSON output
- A topic with missing `sources` gets `severity: fail`
- A plan with no `## Verification` section gets `severity: warn`
- A research document is NOT checked by `check_last_validated` (not applicable)
- Adding a mock 5th document type to dispatch tables causes its validators to run
  without code changes
- `python3 -m pytest tests/test_validators.py tests/test_cross_validators.py tests/test_tier2_triggers.py -v` passes
- CI exit code is 1 when any issue has `severity: fail`
