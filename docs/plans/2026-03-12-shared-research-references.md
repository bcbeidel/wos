---
name: Shared Research References
description: Consolidate duplicated research/distill methodology into shared reference files under _shared/references/
type: plan
status: completed
related:
  - docs/designs/2026-03-12-shared-research-references-design.md
---

# Shared Research References

**Goal:** Eliminate ~900 lines of duplicated research and distillation
methodology by moving all reference files into `skills/_shared/references/`,
splitting monolithic files into self-evident per-phase files, and rewiring
all three consuming skills to point at the shared location. After this
change, methodology updates happen in one place.

**Scope:**

Must have:
- 12 shared research reference files (10 research phases + 2 cross-cutting)
- 2 shared distill reference files
- All 3 skills (research, execute-plan, distill) referencing shared files
- Execute-plan's pipeline template updated to reference shared files
- Old duplicated files deleted
- No content loss from current references

Won't have:
- Agent definitions (`agents/` directory) — separate future initiative
- Changes to SKILL.md body content (mode detection, phase gates, examples)
- Changes to Python scripts or test files
- Changes to execute-plan's non-research references (execution-guide, parallel-dispatch, recovery-patterns, multi-session-resumption)

**Approach:** Work in three chunks. First, create all 14 shared reference
files by splitting monolithic files and reconciling divergences between
the research skill's references and execute-plan's expanded payload (taking
the more complete version). Second, rewire each skill's SKILL.md references
and update the pipeline template. Third, delete old files and validate no
content was lost.

For content reconciliation: where the research skill's brief summary and
execute-plan's expanded payload diverge, the shared file takes the payload's
version (it was expanded for autonomous use and is more self-contained).

**File Changes:**

Create:
- `skills/_shared/references/research/frame.md`
- `skills/_shared/references/research/resumption.md`
- `skills/_shared/references/research/gather-and-extract.md`
- `skills/_shared/references/research/verify-sources.md`
- `skills/_shared/references/research/evaluate-sources-sift.md`
- `skills/_shared/references/research/challenge.md`
- `skills/_shared/references/research/synthesize.md`
- `skills/_shared/references/research/self-verify-claims.md`
- `skills/_shared/references/research/citation-reverify.md`
- `skills/_shared/references/research/finalize.md`
- `skills/_shared/references/research/research-modes.md`
- `skills/_shared/references/research/cli-commands.md`
- `skills/_shared/references/distill/distillation-guidelines.md`
- `skills/_shared/references/distill/mapping-guide.md`

Modify:
- `skills/research/SKILL.md` (references section only)
- `skills/execute-plan/SKILL.md` (references section only)
- `skills/distill/SKILL.md` (references section only)
- `skills/execute-plan/references/research-distill-pipeline.md` (subagent prompt templates)

Delete:
- `skills/research/references/research-workflow.md`
- `skills/research/references/source-quality.md`
- `skills/research/references/challenge.md`
- `skills/research/references/claim-verification.md`
- `skills/research/references/synthesis-guide.md`
- `skills/research/references/research-modes.md`
- `skills/research/references/python-utilities.md`
- `skills/execute-plan/references/research-agent-payload.md`
- `skills/execute-plan/references/distill-mapping-guide.md`
- `skills/distill/references/distillation-guidelines.md`

**Branch:** `shared-research-references`
**PR:** TBD

---

## Chunk 1: Create Shared Reference Files

### Task 1: Move simple reference files to shared directories

Files that move without content changes — just relocate and rename.

**Files:**
- Create: `skills/_shared/references/research/challenge.md`
- Create: `skills/_shared/references/research/research-modes.md`
- Create: `skills/_shared/references/research/cli-commands.md`
- Create: `skills/_shared/references/distill/distillation-guidelines.md`
- Create: `skills/_shared/references/distill/mapping-guide.md`

- [x] Create `skills/_shared/references/research/` directory <!-- sha:7fbf1a0 -->
- [x] Create `skills/_shared/references/distill/` directory <!-- sha:7fbf1a0 -->
- [x] Move `skills/research/references/challenge.md` → `skills/_shared/references/research/challenge.md` (content unchanged) <!-- sha:7fbf1a0 -->
- [x] Move `skills/research/references/research-modes.md` → `skills/_shared/references/research/research-modes.md` (content unchanged) <!-- sha:7fbf1a0 -->
- [x] Move `skills/research/references/python-utilities.md` → `skills/_shared/references/research/cli-commands.md` (rename only, content unchanged) <!-- sha:7fbf1a0 -->
- [x] Move `skills/distill/references/distillation-guidelines.md` → `skills/_shared/references/distill/distillation-guidelines.md` (content unchanged) <!-- sha:7fbf1a0 -->
- [x] Move `skills/execute-plan/references/distill-mapping-guide.md` → `skills/_shared/references/distill/mapping-guide.md` (content unchanged) <!-- sha:7fbf1a0 -->
- [x] Verify: all 5 files exist at new paths with correct content <!-- sha:7fbf1a0 -->
- [x] Commit <!-- sha:7fbf1a0 -->

---

### Task 2: Split research-workflow.md into per-phase files

Extract Phase 1, resumption logic, Phase 2, and Phase 9 from `research-workflow.md` into discrete shared files. Phase 2 and Phase 9 reconcile with the expanded versions from `research-agent-payload.md`, taking the more complete content.

**Files:**
- Create: `skills/_shared/references/research/frame.md`
- Create: `skills/_shared/references/research/resumption.md`
- Create: `skills/_shared/references/research/gather-and-extract.md`
- Create: `skills/_shared/references/research/finalize.md`

**Source material:**
- `skills/research/references/research-workflow.md` — Phase 1 (lines 21-48), resumption (lines 7-19), Phase 2 (lines 49-115), Phase 9 (lines 157-192)
- `skills/execute-plan/references/research-agent-payload.md` — Phase 2 (lines 41-122), Phase 9 (lines 404-435)

- [x] Create `frame.md` from research-workflow.md Phase 1 content (question framing, sub-questions, research brief writing, source diversity note) <!-- sha:88f2dfd -->
- [x] Create `resumption.md` from research-workflow.md resumption section (how to detect current phase from disk state) <!-- sha:88f2dfd -->
- [x] Create `gather-and-extract.md` by reconciling research-workflow.md Phase 2 with payload Phase 2, taking the more complete version (search budgets, per-sub-question cycle, extract format, deferred sources, DRAFT verification) <!-- sha:88f2dfd -->
- [x] Create `finalize.md` by reconciling research-workflow.md Phase 9 with payload Phase 9, taking the more complete version (restructure, format search protocol, remove DRAFT, verify claims, reindex) <!-- sha:88f2dfd -->
- [x] Verify: all 4 files exist, each is self-contained (no dangling references to other phase files) <!-- sha:88f2dfd -->
- [x] Commit <!-- sha:88f2dfd -->

---

### Task 3: Split source-quality.md and claim-verification.md into per-phase files

Split the two multi-phase reference files into discrete per-phase files. Also expand `synthesis-guide.md` into `synthesize.md` using the payload's more complete version.

**Files:**
- Create: `skills/_shared/references/research/verify-sources.md`
- Create: `skills/_shared/references/research/evaluate-sources-sift.md`
- Create: `skills/_shared/references/research/self-verify-claims.md`
- Create: `skills/_shared/references/research/citation-reverify.md`
- Create: `skills/_shared/references/research/synthesize.md`

**Source material:**
- `skills/research/references/source-quality.md` — Phase 3 (lines 1-26), Phase 4 (lines 27-75)
- `skills/research/references/claim-verification.md` — Phase 7 (lines 1-46), Phase 8 (lines 47-75)
- `skills/research/references/synthesis-guide.md` — Phase 6 (all 20 lines)
- `skills/execute-plan/references/research-agent-payload.md` — Phase 3 (lines 125-155), Phase 4 (lines 157-213), Phase 6 (lines 280-303), Phase 7 (lines 310-357), Phase 8 (lines 361-400)

- [x] Create `verify-sources.md` by reconciling source-quality.md Phase 3 with payload Phase 3 (URL verification command, result handling, example progression table) <!-- sha:fae2844 -->
- [x] Create `evaluate-sources-sift.md` by reconciling source-quality.md Phase 4 with payload Phase 4 (SIFT steps, intensity by mode table, source hierarchy T1-T6, authority annotations, red flags) <!-- sha:fae2844 -->
- [x] Create `synthesize.md` by reconciling synthesis-guide.md with payload Phase 6 (confidence levels table, writing constraints, counter-evidence requirement) <!-- sha:fae2844 -->
- [x] Create `self-verify-claims.md` by reconciling claim-verification.md Phase 7 with payload Phase 7 (claim types, table format, CoVe procedure, contradiction resolution) <!-- sha:fae2844 -->
- [x] Create `citation-reverify.md` by reconciling claim-verification.md Phase 8 with payload Phase 8 (re-fetch procedure, resolution statuses table, human-review triggers, example flow) <!-- sha:fae2844 -->
- [x] Verify: all 5 files exist, each is self-contained, no `unverified` references to sibling phase files for core content <!-- sha:fae2844 -->
- [x] Commit <!-- sha:fae2844 -->

---

## Chunk 2: Rewire Skills and Update Pipeline

### Task 4: Update research skill references

Update the research SKILL.md to reference shared files instead of local references.

**Files:**
- Modify: `skills/research/SKILL.md` (references frontmatter only)

- [x] Replace the `references:` block in research SKILL.md frontmatter to point at `../_shared/references/research/*` files and `../_shared/references/preflight.md` <!-- sha:e770a38 -->
- [x] Update any in-body references to `references/research-workflow.md` → appropriate shared file <!-- sha:e770a38 -->
- [x] Update any in-body references to `references/source-quality.md`, `references/challenge.md`, `references/synthesis-guide.md`, `references/claim-verification.md`, `references/research-modes.md` → corresponding shared file paths <!-- sha:e770a38 -->
- [x] Verify: `grep -r 'references/' skills/research/SKILL.md` shows only `../_shared/` paths <!-- sha:e770a38 -->
- [x] Commit <!-- sha:e770a38 -->

---

### Task 5: Update execute-plan skill references and pipeline template

Update execute-plan SKILL.md to drop the deleted payload/mapping references and add shared references for its foreground needs. Update the pipeline template to reference shared files instead of inlining the payload.

**Files:**
- Modify: `skills/execute-plan/SKILL.md` (references frontmatter only)
- Modify: `skills/execute-plan/references/research-distill-pipeline.md` (subagent prompt templates in Phases 2 and 6)

- [x] Replace `references/research-agent-payload.md` and `references/distill-mapping-guide.md` in execute-plan SKILL.md with shared references <!-- sha:2e4123b -->
- [x] In `research-distill-pipeline.md` Phase 1, update mode detection reference to point at shared `research-modes.md` <!-- sha:2e4123b -->
- [x] In `research-distill-pipeline.md` Phase 2, replace `[Full content of research-agent-payload.md inlined here]` with explicit list of shared reference files to read and inline <!-- sha:2e4123b -->
- [x] In `research-distill-pipeline.md` Phase 5, update `distill-mapping-guide.md` reference to shared `mapping-guide.md` <!-- sha:2e4123b -->
- [x] In `research-distill-pipeline.md` Phase 6, update distill subagent template to reference shared `distillation-guidelines.md` <!-- sha:2e4123b -->
- [x] Verify: `grep -r 'research-agent-payload\|distill-mapping-guide' skills/execute-plan/` returns no matches <!-- sha:2e4123b -->
- [x] Commit <!-- sha:2e4123b -->

---

### Task 6: Update distill skill references

Update distill SKILL.md to reference shared files.

**Files:**
- Modify: `skills/distill/SKILL.md` (references frontmatter only)

- [x] Replace `references/distillation-guidelines.md` in distill SKILL.md with `../_shared/references/distill/distillation-guidelines.md` and add `../_shared/references/distill/mapping-guide.md` <!-- sha:f74fdce -->
- [x] Verify: `grep -r 'references/' skills/distill/SKILL.md` shows only `../_shared/` paths <!-- sha:f74fdce -->
- [x] Commit <!-- sha:f74fdce -->

---

## Chunk 3: Clean Up and Validate

### Task 7: Delete old files and validate

Remove all old reference files, clean up empty directories, run tests, and audit for content loss.

**Files:**
- Delete: `skills/research/references/research-workflow.md`
- Delete: `skills/research/references/source-quality.md`
- Delete: `skills/research/references/challenge.md`
- Delete: `skills/research/references/claim-verification.md`
- Delete: `skills/research/references/synthesis-guide.md`
- Delete: `skills/research/references/research-modes.md`
- Delete: `skills/research/references/python-utilities.md`
- Delete: `skills/execute-plan/references/research-agent-payload.md`
- Delete: `skills/execute-plan/references/distill-mapping-guide.md`
- Delete: `skills/distill/references/distillation-guidelines.md`

- [x] Delete all 10 old reference files listed above <!-- sha:f3e968d -->
- [x] Remove `skills/research/references/` directory if empty <!-- sha:f3e968d -->
- [x] Remove `skills/distill/references/` directory if empty <!-- sha:f3e968d -->
- [x] Verify: `ls skills/_shared/references/research/` shows 12 files, `ls skills/_shared/references/distill/` shows 2 files <!-- sha:f3e968d -->
- [x] Verify: `uv run python -m pytest tests/ -v` passes (300 passed) <!-- sha:f3e968d -->
- [x] Content audit: confirm every section heading and instruction from `research-agent-payload.md` appears in exactly one shared file <!-- sha:f3e968d -->
- [x] Verify: no remaining references to deleted file paths across all SKILL.md files <!-- sha:f3e968d -->
- [x] Commit <!-- sha:f3e968d -->

---

## Validation

- [ ] `ls skills/_shared/references/research/ | wc -l` — returns 12
- [ ] `ls skills/_shared/references/distill/ | wc -l` — returns 2
- [ ] `ls skills/research/references/ 2>/dev/null` — directory does not exist or is empty
- [ ] `ls skills/distill/references/ 2>/dev/null` — directory does not exist or is empty
- [ ] `test ! -f skills/execute-plan/references/research-agent-payload.md` — file does not exist
- [ ] `test ! -f skills/execute-plan/references/distill-mapping-guide.md` — file does not exist
- [ ] `grep -c '_shared/references/' skills/research/SKILL.md` — returns 13 (12 research + preflight)
- [ ] `grep -c '_shared/references/' skills/distill/SKILL.md` — returns 3 (2 distill + preflight)
- [ ] `uv run python -m pytest tests/ -v` — all tests pass
- [ ] No references to deleted filenames across skill files: `grep -r 'research-agent-payload\|distill-mapping-guide\|research-workflow\|source-quality\|python-utilities\|synthesis-guide' skills/*/SKILL.md skills/*/references/*.md` — returns no matches
