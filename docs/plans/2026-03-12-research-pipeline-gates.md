---
name: Research Pipeline Gates
description: Lift interactive gates into execute-plan, make research/distill subagents self-contained
type: plan
status: completed
related:
  - docs/designs/2026-03-12-research-pipeline-gates-design.md
---

# Research Pipeline Gates

**Goal:** Fix four problems in the execute-plan research-distill pipeline: (1) research subagents dispatch without user review of briefs, (2) ~14% of background agents fail on plugin cache reads, (3) distillation forces 1:1 mapping, (4) restructuring can drop verified findings. All interactive gates move into execute-plan's foreground; subagents become self-contained autonomous workers.

**Scope:**

Must have:
- 7-phase pipeline replacing current 3-phase pipeline
- Research agent payload with full-fidelity Phase 2-9 instructions
- Distill mapping guide with boundary heuristics
- Completeness constraint in distillation guidelines
- Updated execute-plan SKILL.md references

Won't have:
- Changes to research SKILL.md (standalone interactive skill unchanged)
- Changes to distill SKILL.md (standalone interactive skill unchanged)
- New Python code or scripts (all changes are skill reference docs)
- Changes to parallel-dispatch.md or other execute-plan references

**Approach:** All changes are to skill reference documents under `skills/execute-plan/references/` and `skills/distill/references/`. The research-agent-payload assembles existing content from research skill references (Phases 2-9) into a single self-contained document — faithful repackaging, not a rewrite. The pipeline doc is rewritten from 3 phases to 7 with explicit entry conditions, actions, and gates at each phase. The distill-mapping-guide is new content providing boundary heuristics for the foreground mapping agent.

**File Changes:**
- Create: `skills/execute-plan/references/research-agent-payload.md`
- Create: `skills/execute-plan/references/distill-mapping-guide.md`
- Modify: `skills/execute-plan/references/research-distill-pipeline.md` (3-phase → 7-phase rewrite)
- Modify: `skills/execute-plan/SKILL.md` (add 2 new references to frontmatter)
- Modify: `skills/distill/references/distillation-guidelines.md` (add completeness constraint)

**Branch:** feat/research-pipeline-gates
**PR:** TBD

---

### Task 1: Create research-agent-payload.md

Assemble a self-contained reference containing full-fidelity Phase 2-9
research instructions. This is what execute-plan inlines into each
research subagent's prompt. Source content from:

- `skills/research/references/research-workflow.md` (Phases 2-9)
- `skills/research/references/source-quality.md` (SIFT, tiers, URL verification)
- `skills/research/references/challenge.md` (assumptions, ACH, premortem)
- `skills/research/references/synthesis-guide.md` (confidence levels)
- `skills/research/references/claim-verification.md` (CoVe, claims table)
- `skills/research/references/research-modes.md` (mode matrix, search budgets)
- `skills/research/references/python-utilities.md` (CLI commands)

The payload must:
- Include all phase gates from Phase 2 through Phase 9
- Include the quality checklist (adapted: Phase 1 gate removed since framing is pre-approved)
- Assume the subagent receives an approved research brief as input (question, sub-questions, mode, search strategy)
- Include output document format and frontmatter template
- Reference `<plugin-scripts-dir>` for CLI commands (same convention as other references)
- NOT include Phase 1 (framing) — that's handled by execute-plan before dispatch
- NOT include resumption assessment — subagents run start-to-finish

**Files:**
- Create: `skills/execute-plan/references/research-agent-payload.md`

- [x] Assemble Phase 2-9 instructions with supporting reference content into a single document <!-- sha:082b302 -->
- [x] Verify: document includes all 8 phase gates (Phase 2→3 through Phase 9→Done) <!-- sha:082b302 -->
- [x] Verify: document includes mode matrix, SIFT procedures, challenge templates, claim verification <!-- sha:082b302 -->
- [x] Commit <!-- sha:082b302 -->

---

### Task 2: Create distill-mapping-guide.md

Write guidance for the foreground distill agent that analyzes completed
research docs and proposes N:M finding-to-context-file mappings. This is
new content — no existing reference to assemble from.

Cover:
- How to identify concept boundaries within and across research docs
- Splitting heuristics: when one research doc should produce multiple context files
- Merging heuristics: when findings across research docs should combine
- The "one concept" test: describable in one sentence without "and"
- Preference for granular files (retrieval precision over file count reduction)
- Proposal table format: Finding | Source Research Doc | Target Context File | Target Area | Words (est.)

**Files:**
- Create: `skills/execute-plan/references/distill-mapping-guide.md`

- [x] Write mapping guide with boundary heuristics and proposal format <!-- sha:fc0d9ed -->
- [x] Verify: document covers splitting, merging, and the one-concept test <!-- sha:fc0d9ed -->
- [x] Commit <!-- sha:fc0d9ed -->

---

### Task 3: Rewrite research-distill-pipeline.md

Replace the current 3-phase pipeline with the 7-phase pipeline from the
design. Each phase specifies entry conditions, actions, and gate.

Phases:
1. Frame (foreground) — generate briefs, user approves/rejects with feedback
2. Research (background, parallel) — dispatch with inlined payload
3. Validate Research (foreground) — audit, structural checks
4. Review (foreground) — present summaries, user reviews
5. Map (foreground) — distill agent proposes N:M mapping, user approves
6. Distill (background, parallel) — write context files per approved mapping
7. Validate Distill (foreground) — audit, index sync, bidirectional links

Include updated subagent prompt templates for both research (Phase 2)
and distill (Phase 6) that reference inlined instructions rather than
skill invocation.

**Files:**
- Modify: `skills/execute-plan/references/research-distill-pipeline.md`

- [x] Rewrite pipeline from 3 phases to 7 with entry/actions/gate for each <!-- sha:c4bf150 -->
- [x] Verify: Phase 1 gate requires user approval of all briefs before dispatch <!-- sha:c4bf150 -->
- [x] Verify: Phase 2 subagent template references inlined payload, not `/wos:research` <!-- sha:c4bf150 -->
- [x] Verify: Phase 5 references `distill-mapping-guide.md` for boundary heuristics <!-- sha:c4bf150 -->
- [x] Verify: Phase 6 subagent template references inlined instructions, not `/wos:distill` <!-- sha:c4bf150 -->
- [x] Commit <!-- sha:c4bf150 -->

---

### Task 4: Update distillation-guidelines.md

Add a completeness constraint: verified findings must not be dropped or
diluted to achieve U-shape structure. Accuracy and completeness are the
constraints; U-shape is the goal.

**Files:**
- Modify: `skills/distill/references/distillation-guidelines.md`

- [x] Add completeness constraint section <!-- sha:8bd3028 -->
- [x] Verify: existing U-shape guidance preserved, new constraint clearly stated as primary <!-- sha:8bd3028 -->
- [x] Commit <!-- sha:8bd3028 -->

---

### Task 5: Update execute-plan SKILL.md references

Add the two new reference files to the execute-plan SKILL.md frontmatter
so they're loaded when the skill is invoked.

**Files:**
- Modify: `skills/execute-plan/SKILL.md`

- [x] Add `references/research-agent-payload.md` and `references/distill-mapping-guide.md` to the `references:` list <!-- sha:468c4c5 -->
- [x] Verify: `grep -c 'research-agent-payload\|distill-mapping-guide' skills/execute-plan/SKILL.md` returns 2 <!-- sha:468c4c5 -->
- [x] Commit <!-- sha:468c4c5 -->

---

## Validation

- [ ] All 5 new/modified files exist and have valid WOS frontmatter: `uv run scripts/audit.py --root . --no-urls`
- [ ] `research-agent-payload.md` contains all 8 phase gates (Phase 2→Done)
- [ ] `research-distill-pipeline.md` contains all 7 phases with entry/actions/gate structure
- [ ] `distillation-guidelines.md` contains completeness constraint language
- [ ] `execute-plan/SKILL.md` references list includes both new files
- [ ] No changes to `skills/research/SKILL.md` or `skills/distill/SKILL.md`
