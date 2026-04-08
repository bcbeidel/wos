---
name: Evaluation Prompt Template
description: Research-informed prompt structure for evaluating file compliance against a rule
---

# Evaluation Prompt Template

This template defines how to evaluate a single file against a single rule.
The structure is derived from research findings on LLM-as-judge reliability.

## Design Principles

1. **Locked rubric:** Include the full rule file verbatim. Never summarize.
   Summaries cause interpretation drift across evaluations (QWK improvement
   0.5566 → 0.7276 with locked rubrics).
2. **Chain-of-thought first:** Require reasoning before the verdict.
   Structured reasoning improves accuracy by 10-15 percentage points.
3. **Binary output:** PASS or FAIL. Binary evaluation is more reliable
   than graded scales for objective compliance tasks.
4. **One dimension per evaluation:** Evaluate a single rule against a
   single file. Multi-rule prompts degrade accuracy for all rules.

## Prompt Structure

For each rule-file pair, construct the evaluation as follows:

### Step 1: Present the Rule (Verbatim)

Read the entire rule file and present it exactly as written — frontmatter,
intent, and all examples. Do not paraphrase or abbreviate.

### Step 2: Present the Target File

Read the target file content. Include the file path for context.

### Step 3: Reason Through Compliance

Before producing a verdict, work through these questions:

1. What does this rule require? (Restate the intent in your own words)
2. What would a violation look like? (Reference the non-compliant example)
3. What would compliance look like? (Reference the compliant example)
4. Does the target file contain patterns that match the non-compliant
   example? Cite specific lines.
5. Does the target file follow the patterns in the compliant example?

### Step 4: Produce the Verdict

Based on the reasoning:

- **PASS** — the file complies with the rule
- **FAIL** — the file violates the rule; include a one-sentence
  explanation citing specific lines or patterns

## Edge Cases

| Scenario | Verdict | Reason |
|----------|---------|--------|
| Target file is empty | PASS | No content to violate the rule |
| Target file is binary | PASS | Rule evaluation is not applicable |
| Rule scope doesn't match file | Skip | Do not evaluate — not applicable |
| File partially complies | FAIL | Any violation is a failure; cite the specific violation |
| Ambiguous compliance | PASS | When in doubt, pass. False positives erode trust faster than false negatives |

## Research Basis

- Locked rubrics: Hong et al., "Rulers: Locked Rubrics and
  Evidence-Anchored Scoring" (2026)
- Chain-of-thought: Ugare & Chandra, "Agentic Code Reasoning" (2026);
  Confident AI LLM-as-Judge guide (2024)
- Binary evaluation: Li et al., "Grading Scale Impact on
  LLM-as-a-Judge" (2025); Evidently AI guide (2024)
- Independent evaluation: Anthropic, "Demystifying Evals for AI
  Agents" (2026)
- Ambiguity defaults: CardinalOps, "Rethinking False Positives" —
  false positives erode trust faster than false negatives
