---
name: Literal Intent
description: Promote meaningful numeric and string literals to named module-level constants, with `0`, `1`, `-1`, and empty strings exempt.
paths:
  - "**/*.py"
---

Give numeric and string literals that carry meaning a named-constant home at the top of the module — a `30` that represents a timeout or a `100` that represents page size deserves a name; `0`, `1`, `-1`, and empty strings are exempt.

**Why:** A bare `30` in `requests.get(url, timeout=30)` forces the reader to infer the meaning and the unit; `REQUEST_TIMEOUT_SECONDS = 30` teaches both. A page-size `100` repeated across three call sites drifts when one site needs to change. Named constants centralize the adjustment point and document intent. Source principle: *Name intent into the code* (literal-constant subset; Clean Code ch. 17 G25 magic numbers).

**How to apply:** put meaningful literals at module top as `UPPER_SNAKE_CASE` constants. Keep exemptions for trivial values (`0`, `1`, `-1`, `""`, `None` equivalents) and for values whose meaning is fully captured in-place (array indexing, single-use values tightly bound to the literal). Repeated values are the strongest signal a constant is needed.

```python
HTTP_TIMEOUT_SECONDS = 30
PAGE_SIZE = 100
...
response = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
```

**Common fail signals (audit guidance):** `requests.get(url, timeout=30)` with no `REQUEST_TIMEOUT_SECONDS = 30` constant; a page-size `100` repeated across three call sites.
