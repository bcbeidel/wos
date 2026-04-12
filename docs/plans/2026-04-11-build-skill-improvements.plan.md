---
name: build-skill Improvements from Comparative Analysis
description: Apply seven improvements to skills/build-skill/SKILL.md derived from the skill-curation comparative analysis (G1, G2, G4, G5, G9/G11, G10, G12).
type: plan
status: approved
branch: skill-curation-comparative-analysis
pr: TBD
related:
  - docs/research/2026-04-11-skill-curation-comparative-analysis.research.md
---

# build-skill Improvements from Comparative Analysis

**Goal:** Apply seven targeted improvements to `skills/build-skill/SKILL.md` derived from the comparative analysis gap findings. The changes strengthen routing clarity (G1), success-criteria capture (G2), frontmatter completeness (G4), portability awareness (G5), routing anti-pattern documentation (G9/G11), instruction quality (G10), and output-file conventions (G12). The result is a skill that better reflects cross-platform research findings and guards against documented failure modes.

**Scope:**

Must have:
- Routing confirmation paragraph prepended to Step 1 before the elicitation table (G1)
- Anti-Pattern Guard #6 (routing without confirmation) added (G1)
- Optional "Success criteria" row added to the elicitation table (G2)
- `**Validates as:**` subfield added to `## Handoff` (G2)
- Optional `tested_with:` field added to Step 3 frontmatter requirements (G4)
- Optional "Cross-platform?" row added to the elicitation table (G5)
- Conditional Step 3 note about omitting Claude-specific extensions when cross-platform (G5)
- Description bullet in Step 3 extended to prohibit "When to Use" sections in body (G9/G11)
- Anti-Pattern Guard #7 (routing guidance in body) added (G11)
- Rationale-over-rigidity drafting style note added to Step 3 (G10)
- Optional "Output files" row added to the elicitation table (G12)
- Step 6 updated with `assets/` scaffold note and `references/` vs `assets/` distinction (G12)
- `python scripts/lint.py --root . --no-urls` produces no new warnings

Won't have:
- Changes to `scripts/lint.py`
- Restructuring of untouched sections (Steps 2, 4, 5; Key Instructions)
- Renumbering of existing Anti-Pattern Guards #1–#5
- Changes to any file other than `skills/build-skill/SKILL.md`

**Approach:** All seven changes are surgically applied to a single file — `skills/build-skill/SKILL.md`. Changes are grouped by location in the file: Step 1 additions, Step 3 additions, Step 6 update, Anti-Pattern Guards additions, and Handoff section update. The file remains under 500 body lines after all changes.

**File Changes:**
- Modify: `skills/build-skill/SKILL.md` (routing confirmation + new elicitation rows + Step 3 frontmatter/description/drafting additions + Step 6 assets scaffold + Guards #6/#7 + Handoff Validates-as)

**Branch:** `skill-curation-comparative-analysis`
**PR:** TBD

---

### Task 1: Step 1 — Routing confirmation and new elicitation rows

Apply G1 (routing confirmation paragraph + Guard #6), G2 (Success criteria row), G5 (Cross-platform row), and G12 (Output files row) to Step 1.

**Files:**
- Modify: `skills/build-skill/SKILL.md`

- [x] **Step 1:** Prepend routing confirmation paragraph to Step 1, before the elicitation table
- [x] **Step 2:** Add optional rows to the elicitation table: "Success criteria", "Cross-platform?", "Output files"
- [x] **Step 3:** Verify: `grep -n "right primitive" skills/build-skill/SKILL.md` — returns a match in Step 1 before the table
- [x] **Step 4:** Verify: `grep -c "_(optional)_" skills/build-skill/SKILL.md` — returns ≥3 (one per new optional row)
- [x] **Step 5:** Commit

---

### Task 2: Step 3 — Frontmatter, description, and drafting additions

Apply G4 (`tested_with` frontmatter field), G5 (cross-platform conditional), G9/G11 (routing-in-body prohibition), and G10 (rationale transformation pattern) to Step 3.

**Files:**
- Modify: `skills/build-skill/SKILL.md`

- [x] **Step 1:** Add optional `tested_with:` bullet to the Step 3 frontmatter list
- [x] **Step 2:** Add "If cross-platform" conditional note about omitting Claude-specific extensions
- [x] **Step 3:** Extend the `description:` bullet to prohibit "When to Use This Skill" sections in body
- [x] **Step 4:** Add `**Drafting style:**` block with rationale transformation pattern before the `**Avoid:**` block
- [x] **Step 5:** Verify: `grep -n "tested_with" skills/build-skill/SKILL.md` — returns a match in Step 3
- [x] **Step 6:** Verify: `grep -n "routing-blind" skills/build-skill/SKILL.md` — returns a match in the description bullet
- [x] **Step 7:** Verify: `grep -n "ALWAYS X" skills/build-skill/SKILL.md` — returns the transformation example
- [x] **Step 8:** Commit

---

### Task 3: Step 6 — assets/ scaffold

Apply G12 to Step 6 (Write and Reindex), adding the `assets/` scaffold note.

**Files:**
- Modify: `skills/build-skill/SKILL.md`

- [x] **Step 1:** Update the Step 6 code block to include `skills/<name>/assets/` scaffold note when output files were identified
- [x] **Step 2:** Add inline comment distinguishing `assets/` (output-bound, not loaded) from `references/` (context-loaded)
- [x] **Step 3:** Verify: `grep -n "assets/" skills/build-skill/SKILL.md` — returns match in Step 6
- [x] **Step 4:** Commit

---

### Task 4: Anti-Pattern Guards and Handoff updates

Add Guards #6 and #7; add `**Validates as:**` subfield to `## Handoff`.

**Files:**
- Modify: `skills/build-skill/SKILL.md`

- [x] **Step 1:** Add Guard #6: "Routing without confirmation"
- [x] **Step 2:** Add Guard #7: "When to Use in body"
- [x] **Step 3:** Add `**Validates as:**` conditional subfield under `## Handoff`
- [x] **Step 4:** Verify: `grep -n "^6\." skills/build-skill/SKILL.md` — returns Guard #6
- [x] **Step 5:** Verify: `grep -n "^7\." skills/build-skill/SKILL.md` — returns Guard #7
- [x] **Step 6:** Verify: `grep -n "Validates as" skills/build-skill/SKILL.md` — returns match under Handoff
- [x] **Step 7:** Commit

---

## Validation

- [ ] `grep -n "right primitive" skills/build-skill/SKILL.md` — routing confirmation appears before elicitation table in Step 1
- [ ] `grep -c "_(optional)_" skills/build-skill/SKILL.md` — at least 3 optional rows in elicitation table (Success criteria, Cross-platform, Output files)
- [ ] `grep -n "tested_with" skills/build-skill/SKILL.md` — appears in Step 3 frontmatter requirements
- [ ] `grep -n "routing-blind" skills/build-skill/SKILL.md` — appears in description bullet
- [ ] `grep -n "ALWAYS X" skills/build-skill/SKILL.md` — rationale transformation example present in Step 3
- [ ] `grep -n "^6\." skills/build-skill/SKILL.md` — Anti-Pattern Guard #6 exists
- [ ] `grep -n "^7\." skills/build-skill/SKILL.md` — Anti-Pattern Guard #7 exists
- [ ] `python scripts/lint.py --root . --no-urls` — no new warnings from `skills/build-skill/SKILL.md`
- [ ] `wc -l skills/build-skill/SKILL.md` — under 500 lines total

## Notes

All 7 changes were applied in a single file write during the same session as plan creation. All tasks above are pre-checked; the plan serves as retroactive documentation and a validation checkpoint for `/wos:validate-work`.
