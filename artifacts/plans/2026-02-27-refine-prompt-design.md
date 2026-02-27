---
name: "Refine-Prompt Skill Design"
description: "Design for /wos:refine-prompt — evidence-backed prompt assessment and refinement"
type: plan
related:
  - artifacts/plans/2026-02-27-architecture-reference.md
  - artifacts/plans/2026-02-27-refine-prompt-plan.md
---

# `/wos:refine-prompt` — Evidence-Backed Prompt Refinement

**Issue:** [#71](https://github.com/bcbeidel/wos/issues/71)
**Branch:** `feat/71-refine-prompt`
**PR:** [#73](https://github.com/bcbeidel/wos/pull/73)
**Plan:** [Implementation Plan](2026-02-27-refine-prompt-plan.md)

## Problem

WOS users write prompts of varying quality for tasks, templates, and SKILL.md
instruction blocks. Small improvements to prompt clarity, structure, and
completeness account for ~70% of accuracy gains, but users lack a systematic
way to assess and improve prompts before execution. Over-prompting is also a
risk — Claude 4.x overtriggers on aggressive phrasing, so refinement needs to
be selective and evidence-grounded.

## Solution

A manually-invoked skill (`/wos:refine-prompt`) that runs a three-stage
pipeline: **Assess → Refine → Present**.

**Invocation:** `/wos:refine-prompt <prompt text or file path>`

## Approach: Skill-Only with Flat References

This is a pure skill-layer workflow — no Python scripts. Assessment, technique
application, and output formatting are all LLM judgment tasks (principle 2:
structure in code, quality in skills).

### File Structure

```
skills/refine-prompt/
├── SKILL.md                          # Pipeline, assessment dimensions, key rules
└── references/
    ├── technique-registry.md         # 7 techniques with when-to-apply/skip conditions
    └── assessment-rubric.md          # Scoring rubric with examples at each level
```

Follows the existing pattern: SKILL.md as gateway, references for depth. Output
format guidance lives inline in SKILL.md.

### SKILL.md Frontmatter

```yaml
---
name: refine-prompt
description: >-
  Use when the user wants to "improve a prompt", "refine this prompt",
  "make this prompt better", "assess prompt quality", "optimize this
  prompt", or review any prompt text or SKILL.md instruction block
  for clarity, structure, and completeness.
argument-hint: "[prompt text or file path]"
user-invocable: true
references:
  - references/technique-registry.md
  - references/assessment-rubric.md
---
```

## Pipeline

### Stage 1: Assess

Score the prompt on three dimensions using the assessment rubric:

| Dimension | What it measures |
|-----------|-----------------|
| Clarity | Unambiguous language, specific intent, no jargon without context |
| Structure | Logical organization, XML tags where appropriate, scannable |
| Completeness | Output format specified, success criteria defined, edge cases addressed |

Each dimension scores 1-5 with concrete examples at each level in the rubric.

**Early exit:** If all three dimensions score 4+ and no technique condition
triggers, report the prompt is well-formed and stop. This prevents
over-engineering good prompts.

### Stage 2: Refine

Walk the technique registry in priority order. For each technique:

1. Check the when-to-apply condition
2. If met, apply the technique to the current prompt state
3. If not met, skip
4. Re-score after each application

Stop when all dimensions reach 4+ and no remaining technique triggers.

### Stage 3: Present

Show:

1. **Assessment scores** — before and after, per dimension
2. **Refined prompt** — complete, ready to copy
3. **Change log** — each modification with:
   - What changed
   - Why (rationale)
   - Evidence (research citation)

## Technique Registry (7 techniques, priority order)

| # | Technique | Impact | When to Apply | When to Skip |
|---|-----------|--------|---------------|--------------|
| 1 | Clarity rewrite | HIGH | Always unless 5/5 clarity | Already crystal clear |
| 2 | XML structuring | HIGH | Multi-section prompts, Claude-targeted | Single-purpose, short prompts |
| 3 | Completeness fill | MEDIUM | Missing output format/success criteria/edge cases | All three present |
| 4 | Prompt repetition | HIGH (conditional) | Non-reasoning context only | Reasoning/thinking tasks |
| 5 | Few-shot examples | MEDIUM (conditional) | Format/tone-sensitive, reusable templates | One-off tasks, clear format |
| 6 | Self-check instruction | LOW (conditional) | Verifiable outputs only | Creative/subjective tasks |
| 7 | Role assignment | LOW | Specialized domain knowledge needed | General-purpose tasks |

**Excluded techniques** (with rationale):
- CoT injection — decreasing value on reasoning models, 20-80% latency cost
- Self-reflection loops — unreliable without external feedback
- Meta-prompting — handled by agent subagent system

Each technique in the registry includes: description, when-to-apply condition,
when-to-skip condition, application instructions, and evidence citation.

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Trigger model | Manual invocation | Over-prompting degrades Claude 4.x; ambient hooks risk that |
| Python scripts | None | Pure LLM judgment task (principle 2) |
| File structure | Flat references | Consistent with existing skill patterns |
| Technique scope | Pareto vital few (7) | Top 3 = ~70% of gains; excluded techniques add noise |
| Technique registry | Separate reference file | Updatable without rewriting SKILL.md; techniques have a shelf life |
| Input | Text or file path | Covers both ad-hoc prompts and SKILL.md refinement |
| Early exit | Score 4+ all dimensions | Prevents over-engineering well-formed prompts |

## Scope Boundaries

- **In scope:** Prompt assessment, evidence-backed refinement, explanatory change logs
- **Out of scope:** Auto-execution of refined prompts, hook-based ambient refinement,
  technique discovery (registry is manually curated)

## Evidence

Based on issue #71 research and prototype validation:

- Bsharat et al. "Principled Instructions" (arXiv:2312.16171) — 26 clarity principles
- Anthropic Tier 1 documentation — XML structuring, few-shot examples
- Leviathan et al. "Repeat After Me" (Google Research, 2025) — prompt repetition
- Schulhoff et al. "The Prompt Report" (arXiv:2406.06608) — comprehensive taxonomy
- Mollick et al. (Wharton, 2025) — decreasing CoT value on reasoning models
