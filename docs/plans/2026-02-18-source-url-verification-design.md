# Source URL Verification Design

**Issue:** [#6 — feat: source URL verification pass in /wos:research](https://github.com/bcbeidel/wos/issues/6)
**Date:** 2026-02-18
**Status:** Approved

## Problem

The `/wos:research` skill collects sources via web search and applies SIFT
evaluation, but does not mechanically verify that cited URLs resolve or that
cited titles match actual page content. Hallucinated sources — fabricated URLs,
invented paper titles, dead links — can pass through SIFT evaluation undetected
and propagate into downstream context files.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module location | `wos/source_verification.py` | Composable, follows package pattern |
| HTTP library | `requests` | Cleaner API for redirects/timeouts than urllib |
| Title matching | Normalized substring | Simple, no deps, catches arXiv-style mismatches |
| Concurrency | Sequential | 3-10 sources typical, 10s timeout, good enough for v1 |
| Invocation | Agent runs via `python3 -m wos.source_verification` | Deterministic, testable, agent reads structured output |

## Module Interface

**File:** `wos/source_verification.py`

**Core function:**

```python
def verify_sources(sources: list[dict]) -> list[VerificationResult]:
    """Verify a list of {url, title} sources. Returns results for each."""
```

**Input:** List of dicts matching the `Source` model shape: `{"url": "...", "title": "..."}`

**Output:** List of `VerificationResult`:

```python
@dataclass
class VerificationResult:
    url: str
    cited_title: str
    http_status: int | None       # None if DNS/connection failure
    page_title: str | None        # Extracted <title> or None
    title_match: bool | None      # None if page_title couldn't be extracted
    action: str                   # "ok" | "removed" | "flagged"
    reason: str                   # Human-readable explanation
```

**Actions:**

- `ok` — 200 + title matches (or no title to compare)
- `removed` — 404, DNS failure, connection timeout
- `flagged` — title mismatch, 403 paywall, redirect to different domain, 5xx

## HTTP Verification Logic

Per-source flow:

1. `requests.get(url, timeout=10, allow_redirects=True)`
2. Check final status code:
   - **404, DNS error, ConnectionError, Timeout** → action `removed`
   - **403** → action `flagged`, reason "paywall or access restricted"
   - **5xx** → action `flagged`, reason "server error"
   - **301/302 to different domain** → action `flagged`, reason shows redirect target
     (detected by comparing `response.url` domain to original)
   - **200** → proceed to title extraction
3. Extract page title:
   - Parse `<title>` tag from HTML
   - Fallback: first `<h1>` tag
   - If neither found: `page_title = None`, `title_match = None`, action `ok`
4. Title comparison (normalized substring):
   - Lowercase both, strip punctuation, collapse whitespace
   - Check if one is a substring of the other
   - Match → action `ok`
   - No match → action `flagged`, reason shows both titles

Error handling: Network failures caught per-source, never abort the batch.

## Output Format

**JSON (stdout):**

```json
{
  "results": [
    {
      "url": "https://peps.python.org/pep-0008/",
      "cited_title": "PEP 8 – Style Guide",
      "http_status": 200,
      "page_title": "PEP 8 – Style Guide for Python Code",
      "title_match": true,
      "action": "ok",
      "reason": "200 OK, title matches"
    }
  ],
  "summary": {
    "total": 6,
    "ok": 4,
    "removed": 1,
    "flagged": 1
  }
}
```

**Human summary (stderr):**

```
Source verification (6 sources):
  ✓ https://peps.python.org/pep-0008/ — 200 OK, title matches
  ✗ https://fakeblog.example/post — 404 Not Found (REMOVED)
  ⚠ https://arxiv.org/abs/2509.21361 — 200 OK, title mismatch:
      Cited:  "The Maximum Effective Context Window..."
      Actual: "Context Is What You Need..."
      (FLAGGED — update title or verify manually)

Summary: 4 ok, 1 removed, 1 flagged
```

**CLI:** `echo '<json>' | python3 -m wos.source_verification`
- JSON results → stdout
- Human summary → stderr
- Exit code: 0 if no removals, 1 if any sources removed

## Skill Integration

**New file:** `skills/research/references/source-verification.md`
- Instructions for the agent: when to run, how to parse output, what actions to take

**Updated file:** `skills/research/references/research-investigate.md`
- Add "Phase 2.5: Verify Sources" between Gather (phase 2) and Evaluate (phase 3)
- Reference the new source-verification.md

**No changes to:** `skills/research/SKILL.md` (routing unchanged)

**Agent workflow:**
1. Collect sources during research
2. Format as JSON and pipe to verification module
3. Auto-remove sources with action `removed`
4. Flag sources with action `flagged` — show warning, update cited title if mismatch
5. Proceed to write document with cleaned source list
6. If all sources removed, stop and inform user

## Testing

**File:** `tests/test_source_verification.py`

All tests mock `requests.get`. No real HTTP.

| Test | Scenario | Expected |
|------|----------|----------|
| `test_200_title_match` | 200, title matches | action `ok` |
| `test_200_title_mismatch` | 200, title differs | action `flagged` |
| `test_200_no_title_tag` | 200, no `<title>` | action `ok`, title_match `None` |
| `test_404` | 404 response | action `removed` |
| `test_403_paywall` | 403 response | action `flagged` |
| `test_5xx` | 500 response | action `flagged` |
| `test_dns_failure` | ConnectionError | action `removed` |
| `test_timeout` | Timeout | action `removed` |
| `test_redirect_same_domain` | 301 → same domain, 200 | action `ok` |
| `test_redirect_different_domain` | 301 → different domain | action `flagged` |
| `test_title_normalization` | Case/punctuation difference | action `ok` |
| `test_batch_mixed` | Mixed results | Correct summary counts |
| `test_cli_json_output` | `__main__` with JSON stdin | Valid JSON stdout |
| `test_cli_exit_codes` | All ok vs. some removed | Exit 0 vs. 1 |

## Dependencies

Add `requests>=2.28` to `pyproject.toml` alongside existing `pydantic>=2.0`.

## Files Changed

| File | Change |
|------|--------|
| `wos/source_verification.py` | New — core module |
| `wos/__main__.py` or `wos/source_verification.py` `__main__` block | New — CLI entry point |
| `tests/test_source_verification.py` | New — test suite |
| `skills/research/references/source-verification.md` | New — agent instructions |
| `skills/research/references/research-investigate.md` | Updated — add verification phase |
| `pyproject.toml` | Updated — add `requests>=2.28` dependency |
