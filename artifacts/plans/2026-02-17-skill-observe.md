---
document_type: plan
description: "Build the observe skill for tracking document utilization, surfacing usage patterns, and generating data-driven curation recommendations"
last_updated: 2026-02-17
status: draft
related:
  - 2026-02-17-skill-health.md
  - 2026-02-17-skill-maintain.md
  - 2026-02-17-document-type-models.md
  - ../research/2026-02-17-skills-architecture-design.md
---

# Build Observe Skill

## Objective

A `/dewey:observe` skill exists that tracks how agents and humans use the
knowledge base, surfaces usage patterns, and generates data-driven curation
recommendations. Observation data feeds into health (coverage metrics) and
maintain (cleanup and prioritization decisions).

After sufficient data accumulates, running observe produces actionable
recommendations: refresh stale-but-heavily-used content, expand depth on
high-demand topics, archive unused documents, and investigate never-referenced
entries.

## Context

- Skills architecture: `artifacts/research/2026-02-17-skills-architecture-design.md` §3.4
- Design principle #14: Empirical Feedback — observable signals inform curation
- Existing Dewey infrastructure to build on:
  - `utilization.py`: `record_reference()` appends JSONL, `read_utilization()`
    returns per-file stats (count, first/last referenced)
  - `check_knowledge_base.py`: `generate_recommendations()` cross-references
    utilization data against file inventory and health signals
  - Recommendation categories: stale_high_use, expand_depth, low_utilization,
    never_referenced
  - PostToolUse hook on Read tool for auto-capture (designed, not yet wired)
- Storage: `.dewey/utilization/log.jsonl` — append-only JSONL

## Steps

### Auto-Capture: Hook-Based Tracking

1. Implement `scripts/hook_log_access.py` — a PostToolUse hook script that
   fires when the `Read` tool is called on a file inside the knowledge base
   directory. Appends an entry to the utilization log via `record_reference()`.
   Must never fail (wrap in try/except, always exit 0).

2. Implement `scripts/register_hooks.py` — generates the Claude Code hooks
   configuration (`.claude/settings.json` or `hooks/hooks.json`) to wire
   the PostToolUse hook on Read. Idempotent — safe to run multiple times.

3. Wire hook registration into the setup skill's init workflow so new
   knowledge bases get auto-tracking from day one.

### Utilization Data Layer

4. Implement `scripts/utilization.py` with:
   - `record_reference(kb_root, file_path, context)` — append JSONL entry
     with file, timestamp, context (who/what triggered the read)
   - `read_utilization(kb_root)` — aggregate per-file stats: read count,
     first referenced, last referenced, unique contexts
   - `read_utilization_timeseries(kb_root, file_path)` — return chronological
     entries for a specific file (for trend analysis)
   - `purge_old_entries(kb_root, days)` — remove entries older than N days
     to prevent unbounded log growth

5. Write tests for utilization data layer: record/read round-trips, stats
   aggregate correctly, empty log returns empty dict, purge removes old entries

### Recommendations Engine

6. Implement `scripts/recommendations.py` with:
   - `generate_recommendations(kb_root, min_reads, min_days)` — cross-reference
     utilization data against document inventory and health signals
   - Gating: require minimum reads and minimum time span before generating
     recommendations (avoids premature conclusions)
   - Recommendation categories:
     - **stale_high_use**: document read frequently but `last_validated` is old
       — prioritize refreshing
     - **expand_depth**: topic read many more times than its overview — readers
       want more detail, consider splitting or adding companion docs
     - **low_utilization**: document exists but read far below median — consider
       whether it's discoverable or relevant
     - **never_referenced**: document has zero reads after sufficient tracking
       period — investigate: is it linked? Is it needed?
     - **hot_area**: domain area has disproportionately high reads — may need
       more topics or better organization
     - **cold_area**: domain area has very few reads — may be out of scope
   - Output: `{"recommendations": [...], "summary": {...}}` or
     `{"recommendations": [], "skipped": "reason"}`

7. Write tests for each recommendation category with synthetic utilization data

### Observe Skill and Workflows

8. Create `skills/observe/SKILL.md` with skill description, conversational
   triggers ("show usage", "what's being read", "analytics", "recommendations",
   "what should I update"), routing by intent

9. Create `skills/observe/workflows/observe-dashboard.md`:
   - Read utilization data
   - Present summary: total reads, unique files, date range, top 10 most-read
   - Show per-area breakdown: area name, total reads, topic count, avg reads
   - Highlight anomalies: stale-high-use, never-referenced

10. Create `skills/observe/workflows/observe-recommendations.md`:
    - Run `generate_recommendations()`
    - If gated (insufficient data): explain what's needed and when to try again
    - If sufficient data: present recommendations grouped by category,
      sorted by priority (stale_high_use first)
    - For each recommendation: file path, category, reason, suggested action
    - Offer to route to maintain (for fixes) or curate (for new content)

11. Create `skills/observe/workflows/observe-trends.md`:
    - User selects a file or area
    - Show read count over time (weekly buckets)
    - Compare against knowledge base average
    - Note any inflection points (sudden increase/decrease in reads)

### Integration With Other Skills

12. Add `--recommendations` flag to health check CLI so health reports can
    optionally include utilization-based recommendations

13. Add observe data to maintain-cleanup workflow: never-referenced files
    surface as cleanup candidates with utilization evidence

14. Add observe data to curate-add workflow: when user adds a topic in an
    area, show current utilization for that area so they understand demand

## Verification

- PostToolUse hook fires when an agent reads a knowledge base file and
  appends to `.dewey/utilization/log.jsonl`
- Hook script never crashes (exits 0 even on errors)
- `read_utilization()` returns correct counts after 10 recorded references
- `generate_recommendations()` with < min_reads returns `skipped` response
- `generate_recommendations()` with sufficient data returns at least one
  recommendation per applicable category
- A file read 50 times with `last_validated` > 90 days ago produces a
  `stale_high_use` recommendation
- A file with 0 reads after 14+ days of tracking produces a
  `never_referenced` recommendation
- `observe-dashboard` presents readable summary without errors
- `python3 -m pytest tests/test_utilization.py tests/test_recommendations.py -v` passes
- Log purge removes entries older than threshold without affecting newer ones
