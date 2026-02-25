# Challenge Phase

Quality gate between source evaluation and synthesis. Three sub-steps,
applied based on research mode (see research-modes.md for which apply).

## When to Run

After Phase 3 (Verify & Evaluate), before Phase 5 (Synthesize). All
gathered and verified evidence should be available before challenging.

## Sub-Step 1: Assumptions Check (All Modes)

Identify and examine hidden premises before drawing conclusions.

1. List 3-5 key assumptions underlying your emerging findings
2. For each assumption:
   - What evidence supports it?
   - What evidence contradicts it?
   - If this assumption is false, how does it change the findings?
3. Flag assumptions with weak or no supporting evidence
4. Adjust findings to account for uncertain assumptions

**Output in research document:**

### Assumptions Check

| Assumption | Supporting Evidence | Counter-Evidence | Impact if False |
|------------|-------------------|------------------|-----------------|
| [assumption] | [evidence for] | [evidence against] | [impact] |

## Sub-Step 2: Analysis of Competing Hypotheses (Mode-Conditional)

**Triggered for:** deep-dive, options, competitive, feasibility

Systematic evaluation of alternative explanations using ACH methodology.

### Procedure

1. **Generate hypotheses:** List all reasonable explanations or conclusions
   (minimum 3). Include at least one that contradicts your emerging finding.

   > **Anti-anchoring step:** After generating your initial list, explicitly
   > ask: "What explanation would someone who disagrees propose?" Add it.

2. **Build evidence matrix:** For each piece of evidence, rate consistency
   with each hypothesis:
   - **C** (Consistent) — evidence supports this hypothesis
   - **I** (Inconsistent) — evidence contradicts this hypothesis
   - **N** (Neutral) — evidence neither supports nor contradicts

3. **Evaluate:** Select the hypothesis with the fewest inconsistencies
   (not the most consistencies — this is the key ACH insight).

4. **Document:** Include the evidence matrix in the research document.

**Output in research document:**

### Competing Hypotheses

| Evidence | Hypothesis A | Hypothesis B | Hypothesis C |
|----------|-------------|-------------|-------------|
| [evidence 1] | C | I | N |
| [evidence 2] | I | C | C |
| Inconsistencies | 1 | 1 | 0 |

**Selected:** [Hypothesis] — fewest inconsistencies.

**Rationale:** [Why this hypothesis best fits the evidence]

## Sub-Step 3: Premortem (All Modes)

Stress-test conclusions by imagining failure.

1. Assume your main conclusion is **wrong**
2. Generate 3 specific reasons why it could be wrong:
   - What evidence might you be overweighting?
   - What perspective are you missing?
   - What could change that would invalidate this conclusion?
3. For each reason, assess:
   - How plausible is this failure mode? (high / medium / low)
   - Does it warrant softening or qualifying the conclusion?

**Output in research document:**

### Premortem

| Failure Reason | Plausibility | Impact on Conclusion |
|----------------|-------------|---------------------|
| [reason] | medium | Qualifies finding #2 |
| [reason] | low | No change needed |
| [reason] | high | Softened from "should" to "consider" |
