---
name: Guards Name Novel Failure
description: Anti-Pattern Guards name non-obvious failure modes the workflow steps and Key Instructions cannot prevent on their own; a guard that paraphrases a numbered step or restates a Key Instruction is process echo and must be dropped.
paths:
  - "**/SKILL.md"
---

**Why:** Anti-Pattern Guards exist to surface failure modes a literal reading of the workflow misses — pitfalls that emerge from context the steps cannot capture. When a guard's body cites "Step N", "step #N", or paraphrases an explicit Key Instruction, it occupies bullet space that should be earning signal. The reader has already been told to follow the steps; the guard must tell them what *won't* be obvious. Process-echo guards inflate the section, dilute the genuinely non-obvious entries, and create maintenance debt — every workflow renumber requires a sweep across guard bodies. Source principle: `_shared/references/skill-best-practices.md` (Authoring Principles → Anti-Pattern Guards).

**How to apply:** When evaluating a SKILL.md's `## Anti-Pattern Guards`, read each numbered bullet's body in isolation. If removing the surrounding workflow would leave the guard senseless ("run Step 4 before drafting"), the guard is process echo. If the guard names a failure mode that survives without the workflow context (setuid intent, mutable-ref pinning, `pull_request_target` + PR checkout, real secrets in examples), it is signal. The Tier-1 helper `check_guard_step_echo` flags the literal `\bstep\s*#?\d+(\.\d+)?\b` pattern; this Tier-2 dimension covers the broader paraphrase ("Premature implementation", "Skipping the Scope Gate", "Marking completed on failure") that Tier-1 cannot catch.

```markdown
## Anti-Pattern Guards

1. **Setuid scaffolding** — security minefield. Bash setuid scripts run as the owner regardless of the caller and inherit the caller's environment; recommend a compiled wrapper.
2. **Floating `@main` ref in `uses:`** — a fork of the upstream action can mutate the ref between runs and inject code into the workflow. Pin to a SHA.

(Each bullet names a failure mode the workflow steps cannot prevent
by themselves — the reader needs the warning even if every step ran
to spec.)
```

**Common fail signals (audit guidance):**
- Bullet body contains "Step N", "step #N", or "step 3.5"
- Bullet title is "Skipping the [Gate/Step/Check]" or "Premature [X]" with a body that says "do X first"
- Bullet body restates a Key Instruction verbatim or near-verbatim
- Bullet would dissolve if the workflow section above it were rewritten

**Exception:** A guard whose body cites a step number is permitted when the failure mode is *non-obvious* and the step reference is incidental rather than the guard's substance — e.g., "If Intake step 3.5 flagged destructive operations, the draft must wire `--dry-run` into the destructive code path, not just declare the flag" names a substantive primitive-specific failure (declared-but-unused flag) and the step citation is shorthand for "when destructive ops are in scope". When in doubt, ask: would the guard still teach the reader something if the step number were elided? If yes, retain.
