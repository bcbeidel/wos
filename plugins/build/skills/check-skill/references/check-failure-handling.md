---
name: Failure Handling
description: `## Failure modes` must name real failures with concrete recoveries — and any polling/retry/wait step must carry an explicit timeout and backoff.
paths:
  - "**/SKILL.md"
---

Write a failure contract — name specific failure modes tied to specific steps or external calls, give each a concrete recovery action, and bound every polling/retry/wait step with explicit timeout and backoff parameters.

**Why:** Generic recovery text is functionally silence. "If something goes wrong, handle it" gives the agent nothing to execute; it falls back to whatever default behavior it improvises, which differs run to run. "Poll until ready" with no upper bound is an open-ended hang waiting to happen — the agent cannot decide when to give up, so it either thrashes forever or surfaces an arbitrary timeout the user didn't sanction. External calls (network, filesystem, subprocess) without corresponding failure modes leave the agent with no rubric for partial success — does a 403 retry or stop? The contract decides; silence forces guessing.

**How to apply:** For each external call in Steps, name the realistic failure (`ParserError`, HTTP 403, registry timeout) and a concrete recovery (stop and surface the line; surface the missing permission; retry with `2s, 4s, 8s` up to 30s, then surface `registry-unavailable`). Add explicit timeout + backoff to any polling/retry/wait language.

```markdown
## Failure modes
- `pandas.read_csv` raises `ParserError` → surface the line number and stop; do not write partial output.
- `s3:PutObject` returns 403 → surface the missing permission; do not retry.
- Schema-registry request times out → retry once with exponential backoff starting at 2s, up to 30s total; then surface `registry-unavailable`.
```

**Common fail signals (audit guidance):**
- Section exists but lists placeholder failures ("if something goes wrong") with no recovery
- Steps describe polling, waiting, or retrying without naming a timeout and a backoff parameter ("poll until ready" with no upper bound)
- External calls (network, filesystem, subprocess) in Steps with no corresponding failure mode listed
- Recovery actions are generic ("handle the error") rather than specific ("retry once with exponential backoff, then surface `status=timeout`")
