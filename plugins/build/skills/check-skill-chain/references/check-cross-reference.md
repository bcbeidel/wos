---
name: Cross-Reference Plausibility
description: Each step's declared `output_contract` is plausible given the actual output the referenced SKILL.md produces.
paths:
  - "**/*.chain.md"
---

For every step in a `*.chain.md` manifest, the declared `output_contract` must be plausible given what the referenced SKILL.md actually produces. Mismatches surface as `warn` findings — never `fail`.

**Why:** structural lint (delegated to `plugins/wiki/scripts/lint.py`) verifies the manifest is well-formed — skills exist, contracts are declared, gates appear on consequential steps, no cycles. What it cannot verify is whether the *content* of each step's contract matches reality. A step may declare `output_contract: returns a list of validated URLs` while the underlying SKILL.md actually produces a markdown report with embedded URLs. The chain still parses, but the next step's `input_contract` will fail to resolve at execution time. Cross-reference catches this drift between declared and actual contracts before runtime surprises.

**How to apply:** for each step in the manifest:

1. Read the referenced SKILL.md's `## Handoff` (or equivalent) section. Note what the skill actually produces — file types, data structures, side effects, key claims about output.
2. Compare against the step's declared `output_contract`. Look for: (a) shape mismatches (claims to return data when the skill writes a file); (b) missing-detail mismatches (claims a vague "report" when the SKILL.md produces a specific structured artifact, or vice versa); (c) outright contradictions (different file extensions, different data types).
3. Surface mismatches as `warn` findings. Severity is **always WARN** — the user decides whether the manifest's contract or the SKILL.md's actual output is the source of truth. Both editing directions are valid; the audit's job is to flag the discrepancy, not to adjudicate.
4. Be specific in `recommended_changes`: name the discrepancy, name both sides ("manifest says X; SKILL.md says Y"), and suggest the most likely fix (usually the manifest, since it was written second).

```markdown
# Example: a manifest step with a mismatched contract

## Steps

| Step | Skill | Input Contract | Output Contract | Gate |
|---|---|---|---|---|
| 1 | /wiki:research | a topic | a list of citations | none |

# The referenced /wiki:research SKILL.md actually produces
# a research document at .research/<date>-<slug>.research.md.
# A list of citations is part of that document, but not the
# whole output. Surface as WARN — the manifest's contract is
# under-specified.
```

**Common fail signals (audit guidance):**

- Step's `output_contract` says "list of <items>" when the SKILL.md's Handoff says it writes a file (artifact-vs-data shape mismatch).
- Step's `output_contract` is wildly more specific than the SKILL.md describes (over-claiming).
- Step's `output_contract` is wildly more vague than the SKILL.md describes (under-claiming — usually fixable by inheriting the SKILL.md's wording).
- Step references a SKILL.md that doesn't exist — this is a **structural** failure caught by `wiki/lint.py` Tier-1, not by this judgment rule. If lint.py missed it, escalate as a Tier-1 bug, not a Tier-2 finding.

**Exception:** when the SKILL.md's output is intentionally generic (e.g., "produces structured findings — shape varies by primitive") and the manifest specializes it, the specialization is fine. Surface as `pass`. The audit's purpose is catching drift, not enforcing prose conformity.
