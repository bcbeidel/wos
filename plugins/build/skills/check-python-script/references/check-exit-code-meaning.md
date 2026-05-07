---
name: Exit Code Meaning (skill-helper)
description: Skill-helper scripts subdivide non-zero exit codes by recovery class. `0` is success, `2` is user error (caller should fix the input), `≥3` is internal error (caller should retry / surface / fall back). A script that uses only `0` and `1` flattens decisions the caller needs.
paths:
  - "**/*.py"
---

A skill-helper's exit code is a structured signal to the caller. When all non-zero outcomes collapse to a single `1`, the caller cannot distinguish "fix your input" from "retry" from "give up" — and the helper's value as a composable building block degrades.

**Why:** The skill-helper contract calls for distinct exit codes by recovery class. `0` is success. `2` is user error: the caller (and, transitively, the user) needs to change the input or invocation. `3` (or higher) is internal error: the helper itself failed in a way the caller can choose to retry, surface, or fall back from. The Tier-1 rule `skill-helper-distinct-error-codes` checks the *declaration* (at least 2 distinct non-zero exit-code constants); this dimension is the judgment that the *meaning* lines up — a script with `EXIT_USER_ERROR = 2` and `EXIT_INTERNAL_ERROR = 3` declared but with both codes returned interchangeably from the same code path is below the contract.

**How to apply:** find the exit-code constants declared at module scope (e.g., `EXIT_USER_ERROR = 2`, `EXIT_INTERNAL_ERROR = 3`). Trace each `return <CONSTANT>` in `main()` and verify the recovery class matches: user errors (bad payload, missing required field, file-not-found of a user-supplied path) return `EXIT_USER_ERROR`; internal errors (disk full, network timeout, unexpected `Exception`) return `EXIT_INTERNAL_ERROR`. A bare `return 1` or a `return 2` from a code path that's clearly internal is a finding. The docstring or a header comment should name the exit-code meanings briefly.

**Common fail signals (audit guidance):** distinct constants declared but used interchangeably (the same `except` block returns `EXIT_USER_ERROR` regardless of cause); a bare `return 1` in `main()` without a named constant; an internal error returned with `EXIT_USER_ERROR` because the author "didn't want to add a third constant"; no comment or docstring naming exit-code meanings.

**What is NOT a finding:** a script that genuinely has only one failure mode and returns `EXIT_USER_ERROR` for it (recovery class is uniform); KeyboardInterrupt → 130 (signal-conventional, not an error class to subdivide); argparse usage errors → 2 (argparse owns this exit code by convention).
