---
name: Structured Stderr Errors (skill-helper)
description: Skill-helper scripts emit structured JSON to stderr on error, never raw tracebacks. Errors carry a `code`, a `message`, and an optional `hint`; verbose / traceback output is gated behind a `--debug` flag.
paths:
  - "**/*.py"
---

A skill-helper script is read by another agent. The agent's caller (a skill or another script) parses stderr to decide what to do next — surface the error to the user, retry, fall back, abort. Raw Python tracebacks defeat that machine-readability and tell the user only what failed, not why or what to do.

**Why:** The skill-helper contract calls stderr a structured channel: `{"error": "<code>", "message": "<human-readable>", "hint": "<optional recovery>"}`. The `code` is a stable identifier the caller can branch on; the `message` is what reaches the human; the `hint` is the recovery action the human takes. A traceback is a debug artifact, not a contract — useful behind `--debug`, hostile by default. Source principle (skill-helper profile): structured stderr errors enforce the contract every other helper script will follow.

**How to apply:** identify the error paths in `main()`. Each non-zero exit should be preceded by an `emit_error(code, message, hint=None)`-style call (or equivalent) that writes JSON to stderr. The `code` should be a short, stable identifier (`invalid-json`, `missing-required-field`, `disk-full`) — not the exception class name verbatim. Tracebacks belong behind `--debug` (or equivalent verbose flag); the default error path emits the structured envelope and nothing else. Look for `traceback.print_exc()`, bare `raise` from `main()`, or `print(err, file=sys.stderr)` (which emits the exception's `str(...)` rendering, not a structured envelope).

**Common fail signals (audit guidance):** `traceback.print_exc()` in the default error path (no `--debug` gate); `raise` allowed to propagate from `main()` to the `__main__` guard (Python prints the traceback); `print(err, file=sys.stderr)` emitting an unstructured one-liner; an error message that exposes a stack frame literal (`"NoneType has no attribute 'bar'"`) instead of a stable code.

**What is NOT a finding:** debug output behind a `--debug` flag (caller opted in); the structured envelope being emitted via a wrapper helper that the script declares (e.g., `emit_error()` defined as a module-level function); `KeyboardInterrupt` (130) bypassing the structured-stderr requirement (signal-driven exit, not an error path).
