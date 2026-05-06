---
name: Dependency Posture
description: Justify every third-party import against a stdlib equivalent, and prefer the stdlib when it suffices.
paths:
  - "**/*.py"
---

When a third-party dependency is imported, justify the complexity it brings — or replace it with `argparse`, `pathlib`, `json`, `csv`, `subprocess`, `logging`, `tempfile`, or `http.client` when those would suffice.

**Why:** Each third-party dependency is a deployment surface and a potential security-update obligation. Scripts that use stdlib equivalents run anywhere Python runs — no `pip install`, no version conflicts, no supply-chain exposure. `requests.get(url).json()` looks lighter than `urllib.request.urlopen(url) + json.loads()`, but the second form ships with the interpreter. Source principle: *Prefer the standard library.*

**How to apply:** for every non-stdlib import, name the reason the stdlib equivalent cannot meet the need (e.g., `requests` for streaming + retry logic, `pydantic` for runtime schema validation). When the stdlib can do the job, use it. The bar is "the dependency earns its keep," not "the dependency is convenient."

```python
import json
import urllib.request

with urllib.request.urlopen(url, timeout=30) as resp:
    data = json.load(resp)
```

**Common fail signals (audit guidance):** `requests.get(url).json()` where `urllib.request.urlopen(url).read()` + `json.loads()` would do; `pandas.read_csv()` for a 200-row CSV that `csv.DictReader` handles.
