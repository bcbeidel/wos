---
name: Research Pipeline Gates
description: Lift interactive gates into execute-plan foreground, make research/distill subagents self-contained autonomous workers
type: design
status: draft
related:
  - skills/execute-plan/SKILL.md
  - skills/execute-plan/references/research-distill-pipeline.md
  - skills/research/SKILL.md
  - skills/distill/SKILL.md
  - skills/distill/references/distillation-guidelines.md
---

## Purpose

Fix four problems in the execute-plan research-distill pipeline where
background subagents bypass user-facing gates, fail on permissions, and
produce suboptimal distillation output.

**Problems addressed:**
1. Research subagents dispatch without presenting briefs to the user for review
2. ~14% of background agents fail on plugin cache file reads (permissions)
3. Distillation forces 1:1 mapping between research docs and context files
4. Distillation restructuring can silently drop verified findings

**Root cause:** Interactive gates live inside skills that run as background
subagents. Background agents cannot prompt the user. The fix lifts all
interactive gates into execute-plan's foreground conversation and makes
subagents self-contained autonomous workers.

## Behavior

The research-distill pipeline expands from 3 phases to 7:

| Phase | Location | Mode | Description |
|-------|----------|------|-------------|
| 1. Frame | execute-plan | Foreground | Generate research briefs, user approves/rejects with feedback |
| 2. Research | subagents | Background (parallel) | Execute approved briefs with inlined Phase 2-9 instructions |
| 3. Validate Research | execute-plan | Foreground | Run audit, verify outputs are well-formed |
| 4. Review | execute-plan | Foreground | Present summaries, user reviews research docs |
| 5. Map | distill agent | Foreground | Analyze all research, propose N:M finding-to-context-file mapping, user approves |
| 6. Distill | subagents | Background (parallel) | Write context files per approved mapping |
| 7. Validate Distill | execute-plan | Foreground | Run audit, verify index sync, bidirectional links |

### Phase Details

#### Phase 1: Frame (Foreground)

**Entry:** Plan has research tasks pending. Execute-plan is in research-distill
execution mode.

**Actions:**
- For each research task, extract the research question from the plan
- Generate a brief for each: question, 2-4 sub-questions, research mode,
  search strategy, 1-paragraph scope statement
- Present all briefs to the user as a batch

**Gate:** User approves or rejects each brief. Rejected briefs are revised
based on freeform feedback and re-presented. All briefs must be approved
before proceeding to Phase 2.

#### Phase 2: Research (Background, Parallel)

**Entry:** All research briefs approved.

**Actions:**
- Dispatch one background subagent per approved brief
- Each subagent receives: approved brief + full-fidelity Phase 2-9
  research instructions inlined in its prompt
- Subagents do NOT invoke `/wos:research` or read plugin cache files
- Each produces a research document in `docs/research/`

**Gate:** All subagents complete (DONE, NEEDS_HELP, or BLOCKED).
Failed agents are re-dispatched with the same inlined payload. After 3
failures, escalate to user.

#### Phase 3: Validate Research (Foreground)

**Entry:** All research subagents completed successfully.

**Actions:**
- Run `audit.py --root . --no-urls` to check structural validity
- For each research doc, verify: frontmatter present, sources non-empty,
  draft markers removed, findings section exists
- Report any failures to the user

**Gate:** All research docs pass validation. Failures are fixed (by
re-dispatch or manual intervention) before proceeding.

#### Phase 4: Review (Foreground)

**Entry:** All research docs validated.

**Actions:**
- Present a summary of each research doc: title, key findings (with
  confidence levels), source count, limitations
- User reviews the research quality and completeness
- User may request corrections to specific docs

**Gate:** User explicitly approves the research batch. Corrections are
applied before proceeding.

#### Phase 5: Map (Foreground)

**Entry:** Research batch approved by user.

**Actions:**
- Dispatch a foreground distill agent that reads all completed research docs
- Agent identifies discrete findings across the full research corpus
- Agent proposes N:M mapping: which findings become which context files
- Mapping presented as a table: Finding | Source Research Doc | Target
  Context File | Target Area | Words (est.)
- Agent applies boundary heuristics from `distill-mapping-guide.md`

**Boundary heuristics (for the mapping agent):**
- Split when a research doc covers multiple distinct concepts that serve
  different audiences or have independent actionability
- Merge when findings across research docs address the same concept and
  combined content stays under 800 words
- Each context file should pass the "one concept" test: can you describe
  what this file is about in one sentence without using "and"?
- Prefer more granular files over fewer large ones — retrieval precision
  matters more than reducing file count

**Gate:** User approves, edits, or rejects the proposed mapping. Rejected
mappings are revised based on feedback. Approved mapping becomes the
dispatch plan for Phase 6.

#### Phase 6: Distill (Background, Parallel)

**Entry:** Mapping approved by user.

**Actions:**
- Dispatch one background subagent per target context file (or small
  group of related files)
- Each subagent receives: assigned findings, source research doc paths,
  target file path, target area, distillation instructions inlined
- Subagents write context files with proper frontmatter, bidirectional
  links, and confidence annotations
- Completeness constraint: verified findings must not be dropped or
  diluted to achieve U-shape structure

**Gate:** All subagents complete. Failed agents are re-dispatched.

#### Phase 7: Validate Distill (Foreground)

**Entry:** All distill subagents completed.

**Actions:**
- Run `reindex.py --root .` to regenerate indexes
- Run `audit.py --root . --no-urls` to check structural validity
- Verify bidirectional links: each context file links to its source
  research doc, research docs link to generated context files
- Verify index sync: `_index.md` files match directory contents
- Report results to user

**Gate:** All validation passes. Failures are fixed before proceeding
to the next chunk or plan completion.

## Components

### 1. Updated: `research-distill-pipeline.md`
Replace current 3-phase pipeline with the 7-phase pipeline above.
Each phase specifies entry conditions, actions, and gate.

### 2. New: `research-agent-payload.md`
Full-fidelity Phase 2-9 research instructions assembled into a single
self-contained document. This is a repackaging of existing reference
content, not a rewrite. Subagents receive this inlined in their prompt
alongside the approved research brief. Zero plugin cache reads required.

### 3. New: `distill-mapping-guide.md`
Guidance for the foreground distill agent on finding concept boundaries
across research documents. Covers splitting, merging, and boundary
heuristics as described in Phase 5.

### 4. Updated: `distillation-guidelines.md`
Add completeness constraint: verified findings must not be dropped or
diluted to achieve U-shape. Accuracy and completeness are the constraints;
U-shape is the goal. If a finding cannot fit the U-shape without
information loss, preserve the finding as-is.

### 5. Updated: execute-plan `SKILL.md`
Reference the new 7-phase pipeline for research-distill workstreams.
No structural change to the skill — it already defers to
`research-distill-pipeline.md` for this pattern.

## Constraints

- No changes to the research SKILL.md — it remains a standalone
  interactive skill. The payload assembles its reference content.
- No changes to the distill SKILL.md — the foreground mapping agent
  uses its existing analysis capabilities.
- Subagents never invoke `/wos:research` or `/wos:distill` as skills.
  They receive inlined instructions.
- All user-facing gates live in execute-plan's foreground conversation.
  Subagents are fully autonomous once dispatched.
- The research agent payload must maintain full fidelity with Phase 2-9
  instructions. It is a repackaging, not a rewrite.

## Acceptance Criteria

1. Execute-plan presents research briefs to the user before dispatching
   any research subagent
2. User can approve/reject each brief with freeform feedback; rejected
   briefs are revised and re-presented
3. Research subagents receive self-contained instructions — zero plugin
   cache reads required
4. After research completes, execute-plan runs validation and presents
   summaries for user review
5. A foreground distill agent proposes N:M mapping with explicit boundary
   rationale; user approves before dispatch
6. Distill subagents receive approved mappings and write context files
   without information loss
7. After distill completes, execute-plan runs validation (audit, index
   sync, bidirectional links)
