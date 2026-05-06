---
name: Naming
description: Name functions and variables specifically enough to predict behavior, confine single-letter names to local conventions, and never shadow builtins.
paths:
  - "**/*.py"
---

Name functions and variables to state their intent specifically enough that a reader can predict behavior without diving into the body — confine single-letter names to loop counters, math conventions, and comprehensions, and never shadow Python builtins.

**Why:** Code is read far more often than it's written. A name that predicts behavior saves the reader one or more scans of the body; a name like `process(data)` or `tmp` forces the reader to expand it every time. Shadowing `list`, `id`, `file`, or `type` introduces subtle bugs when later code expects the builtin. Source principle: *Name intent into the code* (plus Clean Code ch. 2).

**How to apply:** at module scope, use descriptive names — `parse_csv_rows`, not `process`; `request_timeout_seconds`, not `t`. Single-letter names are acceptable only in tight local-scope conventions like `for i in range(...)`. Audit module- and function-scope names for builtin shadowing (`list`, `id`, `file`, `type`, `dict`, `input`, etc.).

```python
def parse_csv_rows(rows: Iterable[str]) -> list[Row]:
    ...
```

**Common fail signals (audit guidance):** `def process(data):`, `tmp = ...`, `d = ...`, `list = []`, module-level `x = config()` with no meaningful name.
