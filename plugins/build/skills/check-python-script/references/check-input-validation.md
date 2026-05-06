---
name: Input Validation
description: Validate inputs before destructive or expensive work, gate destructive branches behind a consulted dry-run flag, and source credentials and paths from arguments or the environment.
paths:
  - "**/*.py"
---

Validate inputs before any destructive or expensive work, gate destructive branches behind a `--dry-run` (or equivalent confirmation) flag that the destructive branch actually reads, and source credentials, hostnames, and paths from arguments or the environment.

**Why:** "Fail before damage" is cheap to implement and expensive to skip. A `shutil.rmtree()` that runs before the path is checked destroys state on bad input; a `--dry-run` flag that's declared but never consulted is worse than no flag — it implies a safety that isn't there. Hardcoded credentials and hostnames leak through git history and break across environments. Source principles: *Fail loud, fail early, return meaningful codes*; *Hold the safety posture.*

**How to apply:** make input validation the first work `main()` does after argparse — exists/readable/correct-shape checks before any irreversible step. In every destructive branch (delete, overwrite, irreversible network call), read `args.dry_run` (or the confirmation flag) and short-circuit when set. Keep credentials and absolute paths out of string literals — read them from arguments or `os.environ.get(...)`.

```python
for path in args.inputs:
    if not path.exists():
        print(f"skip: {path} does not exist", file=sys.stderr)
        continue
    if args.dry_run:
        print(f"would remove: {path}")
        continue
    shutil.rmtree(path)
```

**Common fail signals (audit guidance):** A `shutil.rmtree()` call that runs before the input path is checked to exist; a `--dry-run` flag that's declared but never consulted in the destructive branch; a hostname embedded in a string literal.
