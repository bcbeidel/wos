# Source Verification Reference

Mechanical URL verification to catch dead links and hallucinated sources.
Run this after gathering sources and before SIFT evaluation.

## When to Run

After Phase 2 (Initial Source Gathering) completes, before Phase 3 (Source
Evaluation). Every source collected during gathering must pass verification
before entering the SIFT pipeline.

## How to Run

Use `wos.url_checker.check_urls()` to verify source URLs are reachable:

```python
from wos.url_checker import check_urls

results = check_urls([
    "https://example.com/page",
    "https://other.com/article",
])

for r in results:
    print(f"{r.url}: reachable={r.reachable}, status={r.status}, reason={r.reason}")
```

Each result has:
- `reachable` — `True` if the URL returned 2xx/3xx, `False` otherwise
- `status` — HTTP status code (0 for connection/DNS failures)
- `reason` — human-readable explanation when `reachable=False`

## What to Do with Results

**Unreachable sources (status 404, 0, DNS failure):** Drop them from your
source list. Do not include them in the research document. Note in your
investigation that N sources were removed during verification.

**Unreachable sources (status 403, 5xx):** The source exists but is
temporarily unavailable or paywalled. Keep the source but note the access
issue.

**All sources unreachable:** If verification removes every source, stop and
inform the user. Do not proceed with empty sources — gather new ones instead.
