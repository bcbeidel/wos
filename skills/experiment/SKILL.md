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
| design | `protocol/hypothesis.md`, `protocol/design.md` | Fill in research question, variables, conditions, sample size |
| audit | `protocol/audit.md` | Complete the tier-appropriate checklist |
| evaluation | `evaluation/criteria.md`, `evaluation/blinding-manifest.json` | Define metrics, rubrics, blinding setup |
| execution | `data/raw/`, `protocol/prompts/` | Collect data, save raw results |
| analysis | `results/analysis.md` | Run `python scripts/analyze.py`, interpret results |
| publication | `CONCLUSION.md`, `README.md` | Write verdict, update README |

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

## Key Rules

- **Don't skip phases.** All tiers use all 6 phases. Depth varies, not count.
- **Check gates before advancing.** Artifact-existence gates prevent premature progression.
- **Show progress every interaction.** Users need to see where they are.
- **Respect tier choice.** Don't impose Confirmatory ceremony on Pilot experiments.
