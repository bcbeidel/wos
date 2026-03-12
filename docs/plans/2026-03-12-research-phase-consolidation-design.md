---
name: Research Phase Consolidation
description: Merge Phases 2 and 3 into a per-sub-question gather-and-extract loop to prevent fetched content from accumulating across sub-questions
type: design
status: draft
related:
  - skills/research/SKILL.md
  - skills/research/references/research-workflow.md
---

# Research Phase Consolidation

## Problem

When researching 3+ sub-questions with 15+ total sources, fetched content
from WebFetch accumulates in the agent's context window. Under the current
workflow, Phase 2 gathers all sources across all sub-questions, then Phase 3
extracts from all of them. By the time extraction finishes, the context
holds raw fetched content for every source — most of which is no longer
needed.

The root cause is that gathering and extraction are separated into two
sequential-across-all-sub-questions phases instead of being paired per
sub-question.

## Solution

Merge Phases 2 (Gather Sources) and 3 (Extract Source Content) into a
single phase that processes one sub-question at a time:

**For each sub-question:**
1. Search (per existing search budget rules)
2. Fetch candidate sources
3. Extract verbatim content relevant to this sub-question
4. Write structured extracts to disk
5. Move to next sub-question

By the time the agent starts the next sub-question, the previous
sub-question's fetched content has been written to disk and is eligible
for context compression. Only the structured extracts persist in the
document.

## Behavior Changes

### Phase structure: 10 phases → 9 phases

| Old # | Old Name | New # | New Name | Change |
|-------|----------|-------|----------|--------|
| 1 | Frame the Question | 1 | Frame the Question | Unchanged |
| 2 | Gather Sources | 2 | Gather and Extract | Merged with old Phase 3; now loops per sub-question |
| 3 | Extract Source Content | — | — | Absorbed into new Phase 2 |
| 4 | Verify Sources | 3 | Verify Sources | Renumbered |
| 5 | Evaluate Sources | 4 | Evaluate Sources | Renumbered |
| 6 | Challenge | 5 | Challenge | Renumbered |
| 7 | Synthesize | 6 | Synthesize | Renumbered |
| 8 | Self-Verify Claims | 7 | Self-Verify Claims | Renumbered |
| 9 | Citation Re-Verify | 8 | Citation Re-Verify | Renumbered |
| 10 | Finalize | 9 | Finalize | Renumbered |

### New Phase 2: Gather and Extract

The sub-question loop replaces the current "gather all, then extract all"
approach. Within the loop, the existing gather and extract behaviors are
unchanged — search budgets, reflection checkpoints, fetch failure handling,
verbatim extraction rules, and extract formatting all carry over.

**New constraint:** Write extracts for the current sub-question to the DRAFT
document on disk before starting the next sub-question. This is the mechanism
that enables context compression between iterations.

**Cross-pollination:** Sources found while searching for sub-question N that
are relevant to sub-question M should be noted (URL + relevance) in a
"deferred sources" list in the DRAFT document for pickup when sub-question M
is processed.

### Phase gate changes

The old gate between Phase 2 → Phase 3 ("DRAFT file exists on disk") is
removed. The new Phase 2 gate becomes: "DRAFT file exists on disk with
structured extracts for all sub-questions."

This is functionally the old Phase 3 gate — confirming that extraction is
complete — but now it verifies per-sub-question completeness.

### Resumption logic changes

The resumption heuristic in `research-workflow.md` currently distinguishes
between "has sources but no extracts" (resume at Phase 3) and "has extracts"
(resume at Phase 4+). Under the new structure:

- Has `sources:` in frontmatter with some extracts present → resume Phase 2
  at the first sub-question without extracts
- Has extracts for all sub-questions → resume at Phase 3 (old Phase 4)

## Scope

### Must have

- `research-workflow.md` updated with merged Phase 2 and renumbered phases
- SKILL.md phase gates table updated with new numbering
- SKILL.md resumption assessment section updated
- `research-modes.md` — no changes needed (mode matrix is phase-agnostic)
- Cross-pollination mechanism (deferred sources list)

### Won't have

- Subagent dispatch — this design solves context pressure through workflow
  restructuring, not parallelism
- Changes to any phase other than the merge of 2+3 — Phases 4-10 (now 3-9)
  are unchanged in behavior, only renumbered
- Changes to the research assessment script — it checks for structural
  markers (sections, draft marker, source count) which remain the same
- Changes to source-quality.md, challenge.md, synthesis-guide.md, or
  claim-verification.md — these reference files are phase-agnostic

## Acceptance Criteria

1. `research-workflow.md` describes a 9-phase process with Phase 2 as a
   per-sub-question gather-and-extract loop
2. All phase references in SKILL.md (gates table, resumption, common
   deviations) use the new numbering
3. The deferred-sources mechanism is documented for cross-sub-question
   source discovery
4. No behavioral changes to phases other than the 2+3 merge
