---
name: "Experiment Framework Design"
description: "Design for /wos:experiment — empirical validation of research claims via template-first experiment framework with double-blind execution"
type: plan
related:
  - docs/plans/2026-02-24-research-skill-enhancement.md
---

# `/wos:experiment` — Empirical Validation of Research Claims

## Problem

During research, we encounter claims from T4-T5 sources (practitioner blogs,
community content) that are interesting but lack peer review. Currently,
`/wos:research` can only flag low confidence and move on. There is no path to
generate new evidence.

## Solution

A template-first experiment framework. A public GitHub repo template
(`experiment-template`) defines the canonical structure for a reproducible
experiment. A WOS skill (`/wos:experiment`) orchestrates filling it in through
6 gated phases with human checkpoints at each gate.

## Approach: Template + Orchestration Skill

**Why template-first:**

- The template *is* the reproducibility guarantee — anyone can clone an
  experiment repo and understand it without WOS installed
- Clean separation: the template defines *structure*, the skill defines
  *process*
- Naturally produces standalone repos (create from template, work through
  phases, push)
- Template can evolve independently of the skill

## Repo Template Structure

```
experiment-template/
  README.md                        # Auto-generated: hypothesis, method, results summary
  PROTOCOL.md                      # Full experiment protocol (pre-registered)
  protocol/
    hypothesis.md                  # Formal hypothesis statement
    design.md                      # Experiment design (variables, conditions, controls)
    audit.md                       # Scientific method audit checklist + findings
  evaluation/
    criteria.md                    # Evaluation criteria (metrics, rubrics)
    blinding-manifest.json         # Condition-to-ID mappings (sealed until Phase 5)
  data/
    raw/                           # Raw experimental data
    processed/                     # Processed/cleaned data
  results/
    analysis.md                    # Statistical analysis and interpretation
    unblinding.md                  # Condition mappings revealed, results attributed
  CONCLUSION.md                    # Final verdict: validated, invalidated, or inconclusive
```

## 6 Phases (Each Gated by Human Approval)

| Phase | Name | Output | Gate |
|-------|------|--------|------|
| 1 | **Frame & Design** | `protocol/hypothesis.md`, `protocol/design.md` — formal hypothesis, independent/dependent variables, conditions, controls, sample size rationale | Human approves experiment design |
| 2 | **Audit** | `protocol/audit.md` — checklist against scientific method best practices (internal validity, external validity, construct validity, confounds, statistical power) | Human approves audit passes |
| 3 | **Evaluation Design** | `evaluation/criteria.md`, `evaluation/blinding-manifest.json` — metrics, rubrics, pass/fail thresholds; condition-to-opaque-ID mapping generated and sealed | Human approves evaluation criteria |
| 4 | **Blinded Execution** | `data/raw/` — experiment runs using opaque IDs only; neither executor nor evaluator sees condition assignments; human may run some steps manually | Human confirms data collection complete |
| 5 | **Unblinding & Analysis** | `results/unblinding.md`, `results/analysis.md` — manifest unsealed, conditions mapped to results, statistical analysis applied | Human reviews analysis |
| 6 | **Publication** | `README.md`, `CONCLUSION.md` updated; repo pushed; source URL added to originating WOS research document's `sources:` frontmatter | Human approves publication |

## Double-Blind Architecture

The blinding is enforced by phase separation:

- **Phase 3** generates `blinding-manifest.json` mapping conditions (e.g.,
  "TDD", "no-TDD") to opaque IDs (e.g., "condition-alpha", "condition-beta").
  This file is created but treated as sealed — referenced in design but not
  opened.
- **Phase 4** only uses opaque IDs. Execution scripts, data collection, and
  any intermediate evaluation reference IDs, not condition names.
- **Phase 5** opens the manifest and maps IDs back to conditions. Analysis
  happens only after unblinding.

## Integration with `/wos:research`

When a research document identifies a low-confidence claim that is empirically
testable:

1. User invokes `/wos:experiment` referencing the claim and source research doc
2. Experiment proceeds through 6 phases, producing a standalone repo
3. Phase 6 adds the experiment repo URL to the research document's `sources:`
   list
4. The experiment effectively becomes a T2/T3-tier source (institutional or
   peer-reviewed equivalent, depending on rigor)

## Subject Types

The framework is domain-agnostic. Experiments can have:

- **LLM subjects** — Claude API calls as participants; blinding means prompts
  don't reveal the hypothesis, evaluation by a separate instance
- **Code/system subjects** — benchmarks, automated metrics; blinding means
  reviewers don't know which condition produced which metrics
- **Process subjects** — workflow comparisons; blinding means evaluators assess
  outputs without knowing which process generated them

## Scope Boundaries (v1)

- The framework is domain-agnostic but the template is opinionated about
  structure
- Experiments can have LLM, code/system, or process subjects
- Statistical analysis guidance is provided but human judgment is required for
  method selection
- The skill does not auto-detect testable claims — user must invoke it
  explicitly
- Each experiment is a standalone GitHub repository
- Guided automation with human checkpoints (not fully automated)

## Alternatives Considered

### A: Single Phased Skill (no template)

One `/wos:experiment` skill scaffolds the repo structure inline and walks
through 6 phases. Simpler to build but the repo structure is encoded in skill
prose, not in a reusable template. Reproducibility depends on the skill always
scaffolding consistently.

### C: Research Extension

Add an optional "Experiment" phase to `/wos:research`. Tightest integration but
couples experiments to research (cannot run independently) and overloads an
already complex 6-phase skill.

## Open Questions

- What statistical methods should the framework recommend by default?
- Should the template include CI/CD for automated re-runs?
- How should we handle experiments that require external tools or services?
- Should there be a registry/index of completed experiments across projects?
- What is the minimum sample size guidance for different subject types?
