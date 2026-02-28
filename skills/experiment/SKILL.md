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

## Key Rules

- **Don't skip phases.** All tiers use all 6 phases. Depth varies, not count.
- **Check gates before advancing.** Artifact-existence gates prevent premature progression.
- **Show progress every interaction.** Users need to see where they are.
- **Respect tier choice.** Don't impose Confirmatory ceremony on Pilot experiments.
