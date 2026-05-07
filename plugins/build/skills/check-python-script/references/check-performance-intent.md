---
name: Performance Intent
description: Iterate over text files line by line rather than loading them whole, and avoid materializing lists from generators when single-pass iteration suffices.
paths:
  - "**/*.py"
---

**Why:** Scripts get run on files larger than the author imagined. `open(path).read()` followed by `splitlines()` works fine on the 10 KB sample but OOMs on the 2 GB production input — a failure mode the user shouldn't have to work around. `list(map(f, xs))` for a single iteration pays the materialization cost twice (allocation + traversal) when a generator would stream.
**How to apply:** use line-by-line iteration (`for line in f:`) for text files consumed once; chain generators for transformations; reserve `list()` for cases that genuinely need random access, `len()`, or repeated traversal. The default shape is "stream one record at a time."

```python
with open(path, encoding="utf-8") as f:
    for line in f:
        process(line)
```

**Common fail signals (audit guidance):** `content = open(path).read()` followed by `for line in content.splitlines()`; `list(map(f, xs))` where the result is iterated once; loading a large CSV into memory before filtering.
