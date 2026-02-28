---
name: Experiment Phase 2 — Design & Audit Guidance Plan
description: Step-by-step implementation for expanding SKILL.md with Design and Audit phase guidance
type: plan
related:
  - artifacts/plans/2026-02-27-experiment-skill-phase1-plan.md
  - artifacts/plans/2026-02-25-experiment-framework-design.md
---

# Experiment Phase 2 — Design & Audit Guidance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand `skills/experiment/SKILL.md` with full Design and Audit phase guidance so Claude can walk users through writing protocol files with tier-appropriate depth.

**Architecture:** SKILL.md-only changes. No new Python code, no new tests. Three edits to the same file: add Design phase section, add Audit phase section, update Phase Routing table and add Common Deviations. Each edit is verified by frontmatter parse check and full test suite (regression).

**Tech Stack:** Markdown only. No Python, no dependencies.

**Issue:** [#76](https://github.com/bcbeidel/work-os/issues/76)
**Parent Issue:** [#67](https://github.com/bcbeidel/work-os/issues/67)
**Branch:** `feat/76-experiment-design-audit`
**PR:** TBD

### Progress

- [x] Task 1: Add Design phase guidance
- [x] Task 2: Add Audit phase guidance
- [x] Task 3: Update Phase Routing table and add Common Deviations

---

### Task 1: Add Design Phase Guidance

**Files:**
- Modify: `skills/experiment/SKILL.md`

**Step 1: Add the Design phase section**

Insert the following section after the `### Gate Checking` section (after line 84) and before `## Key Rules` (line 86) in `skills/experiment/SKILL.md`:

```markdown
## Phase: Design

Guide the user through `protocol/hypothesis.md` and `protocol/design.md`.
By the end, `PROTOCOL.md` should have its Overview and Design Summary filled.

### Conversation Flow

**Step 1 — Research question:**

Ask: **"What question are you trying to answer?"**

Accept a natural-language answer. Help refine it into a clear, testable question.

**Step 2 — Variables:**

Ask: **"What are you manipulating (independent variable) and measuring (dependent variable)?"**

Write both to the Variables section of `protocol/hypothesis.md`.

**Step 3 — Tier-specific hypothesis depth:**

| Tier | What to write |
|------|---------------|
| Pilot | Research question only. Skip Expected Direction. |
| Exploratory | Research question + expected direction ("We expect X to outperform Y because...") |
| Confirmatory | Formal falsifiable hypothesis with directionality and minimum meaningful effect size |

Write to `protocol/hypothesis.md`. For Confirmatory, ensure the hypothesis specifies the comparison and direction precisely enough to pre-register.

**Step 4 — Conditions:**

Ask: **"What conditions are you comparing?"**

Fill the Conditions table in `protocol/design.md`:

| Condition | Label | Description |
|-----------|-------|-------------|
| Treatment | (user-provided) | (user-provided) |
| Control | (user-provided) | (user-provided) |

Update `experiment-state.json` with the conditions list:

    uv run <plugin-scripts-dir>/experiment_state.py --root . status

(The `conditions` field in state is informational — it doesn't gate anything.)

**Step 5 — Sample size:**

| Tier | Guidance |
|------|----------|
| Pilot | "Any sample size is fine — you're testing feasibility." |
| Exploratory | Default: 30 paired / 50 independent per condition. Enough for bootstrap CIs. |
| Confirmatory | Ask for power analysis justification. Target: 80% power at expected effect size. |

**Step 6 — Procedure:**

Ask: **"Walk me through one trial — what happens step by step?"**

Write numbered steps to the Procedure section of `protocol/design.md`.

**Step 7 — Environment & Model Configuration:**

If the experiment involves LLMs or APIs:
- Pin the exact model string (not an alias)
- Record API parameters (temperature, top_p, max_tokens, seed)
- Record runtime environment

If not applicable, note "N/A — not an LLM/API experiment."

**Step 8 — Reproducibility checklist:**

Walk through the tier-appropriate items in `protocol/design.md`:

| Tier | Items |
|------|-------|
| All | Model pinned, API params recorded, prompts saved, dependencies locked, raw data preserved |
| Exploratory+ | Multiple runs per condition (>=3), full API responses cached, exact rerun commands |
| Confirmatory | Docker environment, analysis code committed before data, independent rerun, archival planned |

**Step 9 — PROTOCOL.md summary:**

Fill the Overview and Design Summary sections of `PROTOCOL.md`:
- Title, Tier, Question (from hypothesis)
- Conditions, Sample, Primary metric (from design)
- 2-3 sentence method summary

### Quality Check

Before advancing, verify:
- [ ] `protocol/hypothesis.md` has a clear research question
- [ ] `protocol/design.md` has conditions, sample size, and procedure
- [ ] For Confirmatory: hypothesis is falsifiable with specified direction
- [ ] `PROTOCOL.md` Overview and Design Summary are filled

Then check gates and advance:

    uv run <plugin-scripts-dir>/experiment_state.py --root . check-gates
    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase design
```

**Step 2: Verify SKILL.md frontmatter still parses**

Run: `uv run python -c "from wos.frontmatter import parse_frontmatter; text = open('skills/experiment/SKILL.md').read(); fm, _ = parse_frontmatter(text); print(fm['name'])"`
Expected: `experiment`

**Step 3: Verify all existing tests pass**

Run: `uv run python -m pytest tests/ -v`
Expected: 208 tests pass, 0 failures.

**Step 4: Commit**

```bash
git add skills/experiment/SKILL.md
git commit -m "feat(experiment): add Design phase guidance with tier branching (#76)"
```

---

### Task 2: Add Audit Phase Guidance

**Files:**
- Modify: `skills/experiment/SKILL.md`

**Step 1: Add the Audit phase section**

Insert the following section immediately after the `## Phase: Design` section (after its Quality Check block) and before `## Key Rules`:

```markdown
## Phase: Audit

Guide the user through the self-review checklist in `protocol/audit.md`.
The checklist scales with tier — Pilot has 5 items, Exploratory adds 10,
Confirmatory adds 5 more.

### Conversation Flow

**Step 1 — Read the protocol:**

Before auditing, read `protocol/hypothesis.md` and `protocol/design.md`
to understand what's being audited.

**Step 2 — Present the tier-appropriate checklist:**

| Tier | Checklist sections to complete |
|------|-------------------------------|
| Pilot | Pilot Checklist only (5 items) |
| Exploratory | Pilot + Exploratory Checklist (15 items) |
| Confirmatory | All three checklists (20 items) |

Tell the user which sections apply: **"Your experiment is [tier], so we'll
work through the [Pilot / Pilot + Exploratory / full] checklist."**

**Step 3 — Walk through each item:**

For each checklist item:
1. State the item
2. Evaluate whether the current protocol satisfies it
3. If not satisfied: suggest a specific fix and which file to update
4. If satisfied: check it off

**Pilot checklist (all tiers):**
- Clear question — can you state what you're learning in one sentence?
- Defined conditions — are treatment and control clearly distinct?
- Measurable outcome — do you know what you'll measure and how?
- Feasible scope — can you realistically collect the planned sample?
- No obvious confounds — is there an alternative explanation you haven't addressed?

**Exploratory additions (+10 items):**
- Operational definitions — variables defined precisely enough for replication?
- Randomization — how are subjects/items assigned to conditions?
- Measurement validity — does the metric capture what you care about?
- Multiple comparisons — planned correction? (analyze.py applies Holm-Bonferroni by default)
- Effect size target — what would a meaningful effect look like?
- Confound inventory — list potential confounds and how each is addressed
- Data collection order — could order bias results? (learning effects)
- Stopping rule — when will you stop collecting data?
- Blinding considered — have you thought about the blinding decision matrix?
- Reproducibility — completed the checklist in `protocol/design.md`?

**Confirmatory additions (+5 items):**
- Pre-registration — analysis plan specified before data collection?
- Power analysis — adequate power (>=80%) at expected effect size?
- Primary vs. secondary outcomes — clearly distinguished?
- Analysis code committed — written and committed before data collection?
- External review — has someone else reviewed the design?

**Step 4 — Record notes:**

Write any concerns, edge cases, or decisions to the Notes section of
`protocol/audit.md`.

**Step 5 — Update PROTOCOL.md:**

Add any Key Decisions made during the audit to the Key Decisions table
in `PROTOCOL.md`.

### Quality Check

Before advancing, verify:
- [ ] All tier-appropriate checklist items addressed
- [ ] For items that aren't satisfied: fixes applied to protocol files
- [ ] Notes section captures any concerns or decisions

Then check gates and advance:

    uv run <plugin-scripts-dir>/experiment_state.py --root . check-gates
    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase audit
```

**Step 2: Verify SKILL.md frontmatter still parses**

Run: `uv run python -c "from wos.frontmatter import parse_frontmatter; text = open('skills/experiment/SKILL.md').read(); fm, _ = parse_frontmatter(text); print(fm['name'])"`
Expected: `experiment`

**Step 3: Verify all existing tests pass**

Run: `uv run python -m pytest tests/ -v`
Expected: 208 tests pass, 0 failures.

**Step 4: Commit**

```bash
git add skills/experiment/SKILL.md
git commit -m "feat(experiment): add Audit phase guidance with tier-scaled checklists (#76)"
```

---

### Task 3: Update Phase Routing Table and Add Common Deviations

**Files:**
- Modify: `skills/experiment/SKILL.md`

**Step 1: Update the Phase Routing table**

Replace the `design` and `audit` rows in the Phase Routing table with references to the new sections. The table (currently at lines 67-74) should become:

```markdown
| Phase | Key Files | Guidance |
|-------|-----------|----------|
| design | `protocol/hypothesis.md`, `protocol/design.md` | See [Phase: Design](#phase-design) below |
| audit | `protocol/audit.md` | See [Phase: Audit](#phase-audit) below |
| evaluation | `evaluation/criteria.md`, `evaluation/blinding-manifest.json` | Define metrics, rubrics, blinding setup |
| execution | `data/raw/`, `protocol/prompts/` | Collect data, save raw results |
| analysis | `results/analysis.md` | Run `python scripts/analyze.py`, interpret results |
| publication | `CONCLUSION.md`, `README.md` | Write verdict, update README |
```

**Step 2: Add Common Deviations section**

Insert this section before `## Key Rules`:

```markdown
## Common Deviations (Do Not)

- **Do not skip the audit.** Even Pilot experiments need the 5-item sanity
  check. Skipping it leads to "I forgot to control for X" after data
  collection.
- **Do not write hypothesis.md and design.md in one pass.** The conversation
  flow asks questions iteratively. Dumping a pre-written protocol bypasses
  the refinement that catches bad designs.
- **Do not impose Confirmatory ceremony on Pilot experiments.** If the tier
  is Pilot, the 5-item checklist is sufficient. Don't add power analysis
  or pre-registration requirements.
- **Do not advance without checking gates.** Always run `check-gates`
  before `advance`. The gates verify artifacts exist on disk.
```

**Step 3: Verify SKILL.md frontmatter still parses**

Run: `uv run python -c "from wos.frontmatter import parse_frontmatter; text = open('skills/experiment/SKILL.md').read(); fm, _ = parse_frontmatter(text); print(fm['name'])"`
Expected: `experiment`

**Step 4: Verify all existing tests pass**

Run: `uv run python -m pytest tests/ -v`
Expected: 208 tests pass, 0 failures.

**Step 5: Run ruff**

Run: `uv run --extra dev ruff check wos/ tests/ scripts/`
Expected: All checks passed.

**Step 6: Commit**

```bash
git add skills/experiment/SKILL.md
git commit -m "feat(experiment): update phase routing table and add common deviations (#76)"
```

**Step 7: Update plan and create PR**

Mark all tasks complete in this plan doc. Commit. Push and create PR:

```bash
git push -u origin feat/76-experiment-design-audit
gh pr create --title "feat: add Design & Audit phase guidance to /wos:experiment (#76)" --body "$(cat <<'EOF'
## Summary

Phase 2 of the experiment framework (#67). Expands SKILL.md with:

- Full Design phase guidance (9-step conversation flow, tier branching)
- Full Audit phase guidance (tier-scaled checklists: 5/15/20 items)
- Updated Phase Routing table with section references
- Common Deviations section (4 anti-patterns)

No new Python code — SKILL.md guidance only.

## Test plan

- [ ] SKILL.md frontmatter parses correctly
- [ ] All existing tests pass (208/208, 0 regressions)
- [ ] `ruff check` clean

Closes #76

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
