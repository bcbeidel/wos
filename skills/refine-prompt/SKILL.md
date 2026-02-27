---
name: refine-prompt
description: >
  This skill should be used when the user wants to "improve a prompt",
  "refine this prompt", "make this prompt better", "assess prompt quality",
  "optimize this prompt", or review any prompt text or SKILL.md instruction
  block for clarity, structure, and completeness.
argument-hint: "[prompt text or file path]"
user-invocable: true
references:
  - references/technique-registry.md
  - references/assessment-rubric.md
---

# Refine Prompt

Assess and refine prompts using evidence-backed techniques. Runs a three-stage
pipeline: **Assess → Refine → Present**.

## Input

Accept either:
- **Inline text** — prompt pasted directly after the command
- **File path** — path to a file containing the prompt (e.g., a SKILL.md)

If a file path is given, read the file and use its content as the prompt.

## Pipeline

### 1. Assess

Score the prompt on three dimensions using the
[assessment rubric](references/assessment-rubric.md):

| Dimension | What it measures |
|-----------|-----------------|
| Clarity | Unambiguous language, specific intent, no undefined jargon |
| Structure | Logical organization, scannable layout, XML tags where useful |
| Completeness | Output format specified, success criteria defined, edge cases addressed |

Each dimension is scored 1-5.

**Early exit:** If all three dimensions score 4+ and no technique condition
in the registry triggers, report that the prompt is well-formed and stop.
Do not refine prompts that don't need it.

### 2. Refine

Walk the [technique registry](references/technique-registry.md) in priority
order (1 through 7). For each technique:

1. Check the **when-to-apply** condition against the current prompt
2. If the condition is met, apply the technique
3. If not, skip to the next technique

Apply techniques iteratively — each builds on the previous output. Stop when
all dimensions reach 4+ and no remaining technique condition triggers.

**Key constraint:** Be selective. Over-prompting degrades Claude 4.x
performance. Apply only techniques whose conditions are clearly met.

### 3. Present

Show the user:

1. **Assessment scores** — before and after, per dimension
2. **Refined prompt** — the complete improved prompt, ready to copy
3. **Change log** — each modification listed with:
   - What changed (brief description)
   - Why (rationale tied to a dimension)
   - Evidence (research citation from the technique registry)

Format the output as:

```
## Assessment

| Dimension | Before | After |
|-----------|--------|-------|
| Clarity | X/5 | Y/5 |
| Structure | X/5 | Y/5 |
| Completeness | X/5 | Y/5 |

## Refined Prompt

[Complete prompt text here, ready to copy]

## Change Log

| # | Change | Rationale | Evidence |
|---|--------|-----------|----------|
| 1 | [What changed] | [Why, tied to dimension] | [Citation] |
```

## Key Rules

- **Manual invocation only.** This skill runs when the user asks. Never
  trigger it automatically or suggest it unprompted.
- **Selective refinement.** Apply only techniques whose conditions are met.
  More techniques ≠ better prompts.
- **Respect well-formed prompts.** If the prompt scores 4+ across all
  dimensions, say so and stop. Don't add noise.
- **Evidence-backed changes.** Every modification in the change log must cite
  the research backing the technique used.
- **Preserve intent.** Refinement improves expression, not meaning. Never
  change what the prompt asks for.
