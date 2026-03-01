---
name: experiment
description: >
  This skill should be used when the user wants to "run an experiment",
  "test a hypothesis", "compare approaches", "validate a claim",
  "set up an experiment", "check experiment status", "experiment progress",
  or any request to conduct a structured empirical investigation using
  the experiment template.
argument-hint: "[action: status, init, or phase name]"
user-invocable: true
compatibility: "Requires Python 3 (stdlib only), experiment-template repo"
references:
  - ../_shared/references/preflight.md
---

# Experiment Skill

Orchestrate structured experiments using repos created from the
[experiment-template](https://github.com/bcbeidel/experiment-template).
Guides users through 6 phases with tier-appropriate depth
(Pilot / Exploratory / Confirmatory).

## Routing

| Situation | Action |
|-----------|--------|
| No `experiment-state.json` | Tell user to create repo from template |
| Has state, user says "status" | Show progress |
| Has state, all phases pending | Initialize (tier selection) |
| Has state, phases in progress | Route to current phase |

**Prerequisite:** Before running any `uv run` command below, follow the
preflight check in the [preflight reference](../_shared/references/preflight.md).

## Detection

Check for `experiment-state.json` in the current directory:

    uv run <plugin-scripts-dir>/experiment_state.py --root . status

If missing: "This doesn't appear to be an experiment repo. Create one from
the template: https://github.com/bcbeidel/experiment-template"

## Initialize

Ask: **"What's the intent of this experiment?"**

| Choice | Tier |
|--------|------|
| Quick test or feasibility check | `pilot` |
| Learn something real, might share results | `exploratory` |
| Testing a specific hypothesis for decisions | `confirmatory` |

Then ask for a short title and run:

    uv run <plugin-scripts-dir>/experiment_state.py --root . init --tier <tier> --title "<title>"

**Escalation prompt:** If the user picks Pilot but mentions sharing results
or making decisions, suggest Exploratory tier.

## Progress Display

Show at each interaction:

    uv run <plugin-scripts-dir>/experiment_state.py --root . status

## Phase Routing

| Phase | Key Files | Guidance |
|-------|-----------|----------|
| design | `protocol/hypothesis.md`, `protocol/design.md` | See [Phase: Design](#phase-design) below |
| audit | `protocol/audit.md` | See [Phase: Audit](#phase-audit) below |
| evaluation | `evaluation/criteria.md`, `evaluation/blinding-manifest.json` | See [Phase: Evaluation Design](#phase-evaluation-design) below |
| execution | `data/raw/`, `protocol/prompts/` | See [Phase: Execution](#phase-execution) below |
| analysis | `results/analysis.md` | See [Phase: Analysis](#phase-analysis) below |
| publication | `CONCLUSION.md`, `README.md` | See [Phase: Publication](#phase-publication) below |

### Gate Checking

Before advancing:

    uv run <plugin-scripts-dir>/experiment_state.py --root . check-gates

If satisfied:

    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase <phase>

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

## Phase: Evaluation Design

Guide the user through `evaluation/criteria.md` and the blinding decision.
If blinding is chosen, generate `evaluation/blinding-manifest.json`.

### Conversation Flow

**Step 1 — Primary metrics:**

Ask: **"What will you measure? How will you measure it?"**

Fill the Primary Metrics table in `evaluation/criteria.md`:

| Metric | Description | How Measured | Direction |
|--------|-------------|--------------|-----------|
| (user-provided) | (user-provided) | (user-provided) | Higher/Lower is better |

**Step 2 — Effect size targets (Exploratory+ only):**

| Tier | Action |
|------|--------|
| Pilot | Skip — you're estimating effect sizes, not targeting them |
| Exploratory | Ask: "What size of difference would be practically meaningful?" |
| Confirmatory | Ask: "What is the minimum effect size of interest (SESOI)?" |

**Step 3 — Evaluation rubric (if human judgment involved):**

If the evaluation method involves human rating or LLM-as-judge, build a
scoring rubric:

| Score | Label | Criteria |
|-------|-------|----------|
| 0 | Fail | (define) |
| 1 | Partial | (define) |
| 2 | Pass | (define) |

**Step 4 — Blinding decision:**

Present the blinding decision matrix:

| Evaluation Method | Pilot | Exploratory | Confirmatory |
|-------------------|-------|-------------|--------------|
| Automated metrics | Label conditions | Label conditions | Label + pre-register |
| Human rating | Label conditions | Label + randomize | Double-blind via script |
| LLM-as-judge | Label conditions | Randomize order + different judge | Randomize + debias |

Ask: **"What evaluation method will you use?"** Then apply the matrix to
recommend a blinding level.

**Step 5 — Generate manifest (if blinding chosen):**

If the matrix recommends blinding, run:

    uv run <plugin-scripts-dir>/experiment_state.py --root . generate-manifest \
      --conditions "label1=desc1,label2=desc2" --seed <seed>

Tell the user: **"The manifest is sealed. During execution, use only the
opaque IDs (ALPHA, BRAVO, etc.). Do not look at the manifest until
the Analysis phase."**

**Step 6 — Pass/fail threshold (Exploratory+ only):**

| Tier | Action |
|------|--------|
| Pilot | Skip |
| Exploratory | Optional — "Under what conditions would you consider the hypothesis supported?" |
| Confirmatory | Required — pre-specify the decision rule |

**Step 7 — Update PROTOCOL.md:**

Fill the Primary Metric field in `PROTOCOL.md` Design Summary.
Add blinding decision to Key Decisions table.

### Quality Check

Before advancing, verify:
- [ ] `evaluation/criteria.md` has at least one primary metric
- [ ] Blinding decision is recorded
- [ ] If blinding chosen: `evaluation/blinding-manifest.json` exists
- [ ] For Confirmatory: pass/fail threshold is specified

Then check gates and advance:

    uv run <plugin-scripts-dir>/experiment_state.py --root . check-gates
    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase evaluation

## Phase: Execution

Guide the user through data collection. If blinding is enabled, enforce
opaque ID usage throughout.

### Conversation Flow

**Step 1 — Blinding check:**

If `evaluation/blinding-manifest.json` has `blinding_enabled: true`:
- **"Blinding is active. Use only opaque IDs (ALPHA, BRAVO, etc.) for
  conditions during this phase. Do not look at the manifest."**
- Do not read or display the manifest contents during this phase.

**Step 2 — Prompt preparation (LLM experiments):**

If the experiment involves LLM subjects:
- Guide creation of prompt files in `protocol/prompts/`
- Each prompt file should be a complete, self-contained prompt
- Use opaque condition IDs in filenames if blinding is active

**Step 3 — Data collection:**

Ask: **"Ready to start collecting data? Walk me through what happens
for each trial."**

Guide the user to save results to `data/raw/`:
- One file per trial, or a structured CSV/JSON
- Include condition identifier (opaque ID if blinded)
- Include all raw output (not just the metric)

**Step 4 — Deviation logging:**

If anything deviates from the protocol during execution:
- Record in the Deviations section of `PROTOCOL.md`
- Include what changed and why

**Step 5 — Completion check:**

When the user reports data collection is complete:
- Verify `data/raw/` contains files (not just `.gitkeep`)
- Confirm the planned sample size was met (or document why not)

### Quality Check

Before advancing, verify:
- [ ] `data/raw/` contains actual data files
- [ ] If blinding: opaque IDs used throughout, manifest not opened
- [ ] Any deviations recorded in `PROTOCOL.md`

Then check gates and advance:

    uv run <plugin-scripts-dir>/experiment_state.py --root . check-gates
    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase execution

## Phase: Analysis

Guide the user through unblinding (if applicable) and statistical analysis.

### Conversation Flow

**Step 1 — Unblinding (if blinding was used):**

If `evaluation/blinding-manifest.json` has `blinding_enabled: true`:

1. Read the manifest: **"Let's unseal the blinding manifest."**
2. Display the condition mapping:
   - "ALPHA was [condition label] — [description]"
   - "BRAVO was [condition label] — [description]"
3. Fill `results/unblinding.md` with the Condition Mapping table
4. Ask: **"Did unblinding reveal anything unexpected?"**
5. Record any observations in Post-Unblinding Notes

If blinding was not used, note "Blinding not used" in `results/unblinding.md`
or delete the file.

**Step 2 — Data preparation:**

Ensure `data/processed/results.csv` exists with:
- A `condition` column (using actual condition labels, not opaque IDs)
- One or more outcome columns matching the primary metrics

If raw data needs processing, guide the user through creating the CSV.

**Step 3 — Run analysis:**

Run the template's analysis script:

    cd <experiment-repo-root>
    python scripts/analyze.py --data data/processed/results.csv --tier <tier>

For within-subjects designs, add `--paired`.

**Step 4 — Interpret results:**

| Tier | Interpretation focus |
|------|---------------------|
| Pilot | "Does this look interesting enough to pursue? What surprised you?" |
| Exploratory | "What do the effect sizes tell you? Are the CIs informative? Does the CI exclude zero?" |
| Confirmatory | "Does the pre-specified analysis support or reject the hypothesis? Report the permutation p-value and effect size together." |

Key guidance:
- Lead with effect sizes, not p-values
- A large effect with a wide CI means you need more data, not that the effect is real
- For Confirmatory: report pre-specified analyses first, post-hoc analyses separately

**Step 5 — Fill `results/analysis.md`:**

- Paste the `analyze.py` output in the Statistical Results section
- Write the Interpretation section
- For Exploratory+: fill the Planned vs. Post-Hoc Analyses table
- Fill Limitations

**Step 6 — Common pitfalls to flag:**

- If the user wants to re-run analysis with different parameters after seeing
  results, warn: **"Changing analysis parameters after seeing data is a form
  of p-hacking. If you want to try different analyses, label them as
  post-hoc/exploratory."**
- If effect size is large but CI is very wide: **"The effect looks large but
  the confidence interval is wide — consider whether you need more data
  before drawing conclusions."**

### Quality Check

Before advancing, verify:
- [ ] `results/analysis.md` has statistical output and interpretation
- [ ] If blinding was used: `results/unblinding.md` is filled
- [ ] Planned vs. post-hoc analyses are distinguished (Exploratory+)

Then check gates and advance:

    uv run <plugin-scripts-dir>/experiment_state.py --root . check-gates
    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase analysis

## Phase: Publication

Guide the user through writing the conclusion, updating the README,
and integrating the experiment as a research source.

### Conversation Flow

**Step 1 — Write CONCLUSION.md:**

Guide the user through each section:

1. **Verdict:** validated / invalidated / inconclusive
   - Base this on the pre-specified threshold (Confirmatory) or the effect
     size and CI (Exploratory)
   - For Pilot: "What did you learn?" is sufficient
2. **Key Findings:** 2-5 bullet points, lead with effect sizes
3. **Practical Implications:** what should change based on results?
4. **Limitations:** be honest about threats to validity
5. **Next Steps:** follow-up experiments or actions

For Confirmatory tier, also fill:
- Pre-Registered Analysis Results section
- Exploratory Findings section (post-hoc, clearly labeled)
- Archival section (persistent identifier, data archive URL)

**Step 2 — Update README.md:**

Fill the README with a summary:
- Experiment title and tier
- One-sentence hypothesis
- One-sentence method
- Key result (effect size + CI)
- Verdict

**Step 3 — Research integration:**

If this experiment was motivated by a research document:

Ask: **"Was this experiment motivated by a specific research document?
If so, which one?"**

If yes:
1. Add the experiment repo URL to the research document's `sources:` list
   in its YAML frontmatter
2. The experiment qualifies as a T2 source (direct empirical evidence)
   or T3 source (structured methodology) depending on tier:
   - Confirmatory → T2 (primary research equivalent)
   - Exploratory → T3 (structured evidence)
   - Pilot → T3 (preliminary evidence)

**Step 4 — Archival (Confirmatory only):**

For Confirmatory tier:
- Verify Docker build works: `docker build -t experiment .`
- Ensure all data, code, and results are committed
- Guide user to archive with a persistent identifier (Zenodo, institutional
  repo, or GitHub release with DOI)

### Quality Check

Before advancing, verify:
- [ ] `CONCLUSION.md` has a verdict and key findings
- [ ] `README.md` is updated with experiment summary
- [ ] For Confirmatory: archival checklist complete

Then advance to mark the experiment complete:

    uv run <plugin-scripts-dir>/experiment_state.py --root . advance --phase publication

Display final progress — all phases should show complete.

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
- **Do not open the blinding manifest during execution.** The whole point
  of blinding is that condition labels are hidden. If you read the manifest
  during Phase 4, blinding is broken.
- **Do not skip the evaluation rubric for subjective metrics.** Without
  a rubric, "quality" means whatever the evaluator feels in the moment.
  Define scoring criteria before collecting data.
- **Do not change analysis parameters after seeing results.** If the
  pre-specified analysis doesn't show what you hoped, that's a finding,
  not an invitation to try different tests. Post-hoc analyses must be
  labeled as exploratory.
- **Do not skip the research integration step.** The whole point of
  running experiments is to generate evidence that feeds back into
  research documents. If the experiment isn't linked as a source,
  it's orphaned knowledge.

## Backtracking

Backtracking returns to an earlier phase. It's re-entry, not undo —
existing artifacts are preserved as `.prev` files.

### When to Suggest Backtracking

- User realizes the hypothesis is wrong during Audit
- Audit reveals a fundamental design flaw
- Execution reveals evaluation criteria need updating
- Analysis shows data collection was flawed

### How to Backtrack

1. Confirm with the user: **"Backtracking to [phase] will reset
   [downstream phases]. Existing work will be saved as .prev files.
   Proceed?"**
2. Run:

       uv run <plugin-scripts-dir>/experiment_state.py --root . backtrack --phase <phase>

3. Show the updated progress display
4. Remind the user: **"Your previous work is saved as .prev files
   if you need to reference it."**

### Rules

- **Always confirm before backtracking.** Show what will be reset.
- **Backtracking preserves artifacts.** Files get a `.prev` suffix, not deleted.
- **Only one level of history.** If `.prev` files already exist, they're overwritten.
- **Backtracking is normal.** Especially at Pilot/Exploratory tiers, changing
  direction is expected and healthy. Don't treat it as failure.

## Key Rules

- **Don't skip phases.** All tiers use all 6 phases. Depth varies, not count.
- **Check gates before advancing.** Artifact-existence gates prevent premature progression.
- **Show progress every interaction.** Users need to see where they are.
- **Respect tier choice.** Don't impose Confirmatory ceremony on Pilot experiments.

## LLM-as-Judge Debiasing

When the evaluation method is "LLM-as-judge," apply these mitigations
during the Evaluation and Execution phases. The biases below are
well-documented in the literature.

### Known Biases and Mitigations

| Bias | Description | Mitigation |
|------|-------------|------------|
| Position bias | LLMs prefer the first or last option presented | Randomize condition order across evaluations. Run each comparison in both orders and average. |
| Verbosity bias | LLMs rate longer responses higher regardless of quality | Normalize response lengths, or instruct the judge to explicitly ignore length. |
| Self-preference | Models rate their own outputs higher | Use a different model family as judge (e.g., use Claude to judge GPT outputs, or vice versa). |
| Anchoring | First example seen influences scoring of later examples | Present conditions independently, not side-by-side. Evaluate each on its own merits. |
| Sycophancy | Model agrees with the framing of the evaluation prompt | Use neutral evaluation prompts. Don't hint at expected outcomes. |

### Calibration Protocol

For Exploratory+ experiments using LLM-as-judge:

1. Create 3-5 "anchor" examples with known quality levels
2. Have the judge evaluate anchors first
3. Verify anchor scores match expected quality ordering
4. If calibration fails, revise the evaluation prompt before proceeding
5. Include anchor evaluation results in `evaluation/criteria.md`

### When to Apply

The Evaluation phase guidance asks for the evaluation method. If the
answer is "LLM-as-judge":
- Exploratory: apply position randomization + self-preference check
- Confirmatory: apply all mitigations + calibration protocol

## Reproducibility

Reproducibility requirements scale with tier. These supplement the
checklist in `protocol/design.md`.

### Key Principle

LLM reproducibility is *distributional*, not exact. Even `temperature=0`
is non-deterministic due to floating-point arithmetic and silent model
updates. Define reproducibility as: "consistent statistical properties
across runs," not "identical outputs."

### Tier Requirements

**All tiers:**
- Model version pinned (exact string like `claude-sonnet-4-20250514`, not alias like `claude-sonnet`)
- API parameters recorded in `protocol/design.md`
- Prompts saved as files in `protocol/prompts/`
- Dependencies in `scripts/requirements.txt`
- Raw data preserved in `data/raw/`

**Exploratory+:**
- Multiple runs per condition (>=3) for variance estimation
- Full API responses cached in `data/raw/` (not just extracted metrics)
- Exact rerun commands in README

**Confirmatory:**
- Docker environment (`Dockerfile.example` in template)
- All analysis code committed before data collection
- Independent re-run verification (someone else runs it)
- Archived with persistent identifier

### Response Caching Strategy

For LLM experiments, cache full API responses:
- Save each response as `data/raw/{condition_id}_{trial_n}.json`
- Include full response object (not just text content)
- This enables re-analysis without re-running the experiment
- Caching is the primary mechanism for reproducibility at Exploratory tier

## Error Recovery

### analyze.py Failures

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| "No 'condition' column" | CSV missing condition column | Ensure `data/processed/results.csv` has a column named `condition` |
| "Not enough data" | Too few rows per condition | Check that all trials are included in the CSV |
| FileNotFoundError | Wrong path or missing file | Verify `data/processed/results.csv` exists |
| Import error | Missing dependency | Run `pip install -r scripts/requirements.txt` in the experiment repo |

### Gate Check Failures

If `check-gates` reports missing artifacts:
1. Read the missing artifact list
2. Determine which phase should have created them
3. The current phase cannot proceed — guide the user to create the missing files
4. Re-run `check-gates` after creating them

### Experiment Abandonment

If the user wants to abandon an experiment mid-flight:
1. Ask why — the reason informs what to document
2. Update `CONCLUSION.md` with verdict "Inconclusive" and document why
3. Record the abandonment reason in `PROTOCOL.md` Deviations
4. The experiment repo remains as a record — don't delete it

### Hypothesis Changes During Design

If the hypothesis changes significantly during the Design phase:
- This is expected and healthy at Pilot/Exploratory tiers
- Update `protocol/hypothesis.md` with the revised question
- If the experiment has progressed past Design, this requires backtracking
  (see Backtracking section)

## Edge Cases

### Single-Condition Experiments

Some experiments measure a single condition against a known baseline
rather than comparing two conditions:
- Valid when the baseline is external (e.g., "industry benchmark")
- Use a one-sample design: one condition, compared against a threshold
- `generate-manifest` is not applicable (no blinding with one condition)
- `analyze.py` can still compute descriptive stats and CIs for the single condition

### More Than Two Conditions

Experiments with 3+ conditions:
- `generate-manifest` supports up to 8 conditions (NATO phonetic alphabet)
- `analyze.py` computes pairwise comparisons with Holm-Bonferroni correction
  for multiple comparisons by default
- Guide the user to specify which comparison is primary vs. secondary
  in `evaluation/criteria.md`

### Mixed Evaluation Methods

Some experiments combine automated metrics with human judgment:
- Apply blinding decision matrix separately for each metric type
- Automated metrics can use condition labels even when human metrics
  are blinded
- Document which metrics use which evaluation method in `evaluation/criteria.md`
