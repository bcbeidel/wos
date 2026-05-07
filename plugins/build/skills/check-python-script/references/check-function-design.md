---
name: Function Design
description: Keep each function single-purpose at one level of abstraction, extract three-or-more near-identical blocks into a shared helper, and avoid conjunction names.
paths:
  - "**/*.py"
---

**Why:** Short, well-named functions read as their own commentary — `main()` becomes a sequence of named operations rather than a 200-line wall. Duplicated blocks drift: fix one copy, forget the others, ship a partial bug. Conjunction names are a smell that the function is doing more than one thing and should be split. Source principles: *Keep functions small and single-purpose*; *Eliminate duplication* (plus Clean Code ch. 3 and Pragmatic Programmer §15 DRY).

**How to apply:** read `main()` aloud — if it doesn't sound like a sequence of named operations, extract the cohesive sections. Helper functions get verb-phrased single-purpose names (`fetch`, `transform`, `validate`, `write`). Three near-identical blocks become a single helper called three times.

```python
def main(argv: list[str] | None = None) -> int:
    args = get_parser().parse_args(argv)
    raw = fetch(args.source)
    records = transform(raw)
    validate(records)
    write(records, args.out)
    return 0
```

**Common fail signals (audit guidance):** A 200-line `main()` that inlines fetch, transform, validate, and write; the same 6-line try/except block copy-pasted three times with different filenames.
