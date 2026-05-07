---
name: Output Discipline
description: Route data output to stdout, log/error/prompt output to stderr, and ensure every error branch produces a non-zero exit code.
paths:
  - "**/*.py"
---

**Why:** Unix pipelines depend on the stdout-for-data, stderr-for-chatter convention; a script that mixes status narration into stdout silently corrupts every caller that consumes its output. Callers in cron, CI, and Make depend on the exit-code contract — an error branch that logs and then `return 0` makes the failure invisible: cron sends no email, CI marks the job green, the bug ships.
**How to apply:** keep `print()` of error or log content off stdout — pass `file=sys.stderr` or use `logging` (configured to stderr). Ensure every documented or implied failure mode results in `return N` where `N > 0`, or `raise`. When the script carries verbosity flags or runs in automation, route operational messages through `logging` rather than `print`.

```python
def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    try:
        return run(args)
    except FileNotFoundError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
```

**Common fail signals (audit guidance):** `print(f"error: {err}")` without `file=sys.stderr`; error branches that log and then `return 0`; `print()` used as a mix of data output and status narration.
