---
name: Research Phase Consolidation
description: Merge research Phases 2+3 into a per-sub-question loop and renumber all subsequent phases
type: plan
status: completed
related:
  - docs/plans/2026-03-12-research-phase-consolidation-design.md
  - skills/research/SKILL.md
  - skills/research/references/research-workflow.md
---

# Research Phase Consolidation

**Goal:** Reduce context window pressure during research by restructuring Phases 2 (Gather) and 3 (Extract) into a single per-sub-question loop. The agent processes one sub-question at a time — search, fetch, extract, write to disk — so fetched content doesn't accumulate across sub-questions.

**Scope:**

Must have:
- Merged Phase 2 with per-sub-question loop and deferred-sources mechanism
- All phase references renumbered across 6 files (10→9 phases)
- Updated resumption logic and phase gates

Won't have:
- Subagent dispatch
- Changes to assessment script (`assess_research.py`)
- Behavioral changes to any phase other than the 2+3 merge
- Changes to `research-modes.md` or `python-utilities.md`

**Approach:** Rewrite `research-workflow.md` Phase 2 as a per-sub-question loop that includes extraction, remove Phase 3, renumber all subsequent phases. Then update every file that references phase numbers: SKILL.md, claim-verification.md, source-quality.md, challenge.md, synthesis-guide.md. Each file is an independent task after the workflow rewrite.

**File Changes:**
- Modify: `skills/research/references/research-workflow.md` (merge Phase 2+3, renumber phases 4-10→3-9, update resumption logic, update quality check)
- Modify: `skills/research/SKILL.md` (phase gates table, workflow summary line, common deviations, examples, key rules)
- Modify: `skills/research/references/claim-verification.md` (Phase 8→7, Phase 9→8)
- Modify: `skills/research/references/source-quality.md` (Phase 4→3, Phase 5→4)
- Modify: `skills/research/references/challenge.md` (Phase 6→5)
- Modify: `skills/research/references/synthesis-guide.md` (Phase 7→6)

**Branch:** `feat/150-research-phase-consolidation`
**PR:** TBD

---

### Task 1: Rewrite research-workflow.md

**Files:**
- Modify: `skills/research/references/research-workflow.md`

- [x] Update header from "Ten-phase process" to "Nine-phase process" <!-- sha:e948c25 -->
- [x] Rewrite resumption logic with new phase numbers (remove Phase 3 entry, shift all others down by one) <!-- sha:e948c25 -->
- [x] Merge Phase 2 (Gather Sources) and Phase 3 (Extract Source Content) into a single "Phase 2: Gather and Extract" with a per-sub-question loop structure: search → fetch → extract → write to disk → next sub-question <!-- sha:e948c25 -->
- [x] Add deferred-sources mechanism: sources found for other sub-questions are noted with URL + relevance for pickup later <!-- sha:e948c25 -->
- [x] Preserve all existing behaviors within the loop: search budgets, reflection checkpoints, fetch failure handling, verbatim extraction format <!-- sha:e948c25 -->
- [x] Renumber Phase 4→3, Phase 5→4, Phase 6→5, Phase 7→6, Phase 8→7, Phase 9→8, Phase 10→9 (content unchanged, just phase headings and any internal cross-references) <!-- sha:e948c25 -->
- [x] Update Quality Check checklist from 10 items to 9 items with new numbering <!-- sha:e948c25 -->
- [x] Verify: `grep -c "^## Phase" skills/research/references/research-workflow.md` returns 9 <!-- sha:e948c25 -->

---

### Task 2: Update SKILL.md phase references

**Files:**
- Modify: `skills/research/SKILL.md`

**Depends on:** Task 1

- [x] Update "All modes follow the same 9-phase workflow" line (already says 9 — confirmed correct) <!-- sha:9943860 -->
- [x] Rewrite phase gates table: remove the 2→3 gate, add new 2→3 gate ("DRAFT file exists with structured extracts for all sub-questions"), renumber remaining gates <!-- sha:9943860 -->
- [x] Update Common Deviations: "written to disk since Phase 2" remains correct; "Phase 7 synthesis" → "Phase 6 synthesis" <!-- sha:9943860 -->
- [x] Update example annotations: "Phase 5 (Evaluate Sources)" → "Phase 4", "Phase 7" → "Phase 6", "Phase 8" → "Phase 7" <!-- sha:9943860 -->
- [x] Update Key Rules: "Phase 2" search logging reference remains correct (still Phase 2) <!-- sha:9943860 -->
- [x] Verify: no remaining references to "Phase 10", "Phase 9" (old numbering for Citation Re-Verify), or "Phase 3: Extract" <!-- sha:9943860 -->

---

### Task 3: Update claim-verification.md phase references

**Files:**
- Modify: `skills/research/references/claim-verification.md`

- [x] Update opening line: "Phase 8" → "Phase 7", "Phase 9" → "Phase 8" <!-- sha:6dd9a8c -->
- [x] Update all internal phase references: Phase 8→7, Phase 9→8 throughout <!-- sha:6dd9a8c -->
- [x] Verify: `grep -c "Phase [0-9]" skills/research/references/claim-verification.md` — confirm only Phase 7 and Phase 8 references remain <!-- sha:6dd9a8c -->

---

### Task 4: Update source-quality.md phase references

**Files:**
- Modify: `skills/research/references/source-quality.md`

- [x] Update opening line: "Phase 4" → "Phase 3", "Phase 5" → "Phase 4" <!-- sha:6dd9a8c -->
- [x] Update all internal phase references: Phase 4→3, Phase 5→4 throughout <!-- sha:6dd9a8c -->
- [x] Verify: `grep -c "Phase [0-9]" skills/research/references/source-quality.md` — confirm only Phase 3 and Phase 4 references remain <!-- sha:6dd9a8c -->

---

### Task 5: Update challenge.md and synthesis-guide.md phase references

**Files:**
- Modify: `skills/research/references/challenge.md`
- Modify: `skills/research/references/synthesis-guide.md`

- [x] challenge.md: "Phase 6" → "Phase 5" <!-- sha:6dd9a8c -->
- [x] synthesis-guide.md: "Phase 7" → "Phase 6" <!-- sha:6dd9a8c -->
- [x] Verify: no old phase numbers remain in either file <!-- sha:6dd9a8c -->

---

### Task 6: Commit and verify

- [x] Run: `uv run python -m pytest tests/ -v` — 300 passed
- [x] Run: `grep -rn "Phase 10\|Phase 9.*Citation\|Phase 3.*Extract" skills/research/` — no matches
- [x] Commit all changes <!-- sha:6dd9a8c -->

---

## Validation

- [x] `grep -c "^## Phase" skills/research/references/research-workflow.md` — returns exactly 9
- [x] `grep -rn "Phase 10" skills/research/` — no matches
- [x] `grep -rn "Phase 3.*Extract" skills/research/` — no matches (old Phase 3 gone)
- [x] `uv run python -m pytest tests/ -v` — 300 passed
- [x] Manual review: Phase 2 in research-workflow.md describes a per-sub-question loop with deferred-sources mechanism
