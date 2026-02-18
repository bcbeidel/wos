# Source Verification Reference

Mechanical URL verification to catch hallucinated sources, dead links, and
title mismatches. Run this after gathering sources and before SIFT evaluation.

## When to Run

After Phase 2 (Initial Source Gathering) completes, before Phase 3 (Source
Evaluation). Every source collected during gathering must pass verification
before entering the SIFT pipeline.

## How to Run

1. Format your collected sources as a JSON array:

   ```json
   [
     {"url": "https://example.com/page", "title": "Page Title"},
     {"url": "https://other.com/article", "title": "Article Title"}
   ]
   ```

2. Pipe the JSON to the verification module:

   ```bash
   echo '[{"url": "...", "title": "..."}]' | python3 -m wos.source_verification
   ```

3. Read the JSON output from stdout. Each result has an `action` field:
   - `ok` -- source verified, keep it
   - `removed` -- source is dead (404, DNS failure, timeout), drop it
   - `flagged` -- source has an issue (title mismatch, paywall, redirect), review it

## What to Do with Results

**`removed` sources:** Drop them from your source list. Do not include them
in the research document. Note in your investigation that N sources were
removed during verification.

**`flagged` sources with title mismatch:** The cited title doesn't match the
actual page title. Update the cited title to match the page title, or
investigate whether the source is actually relevant.

**`flagged` sources with redirect:** The URL redirected to a different domain.
Check if the redirected destination is still the intended source. Update the
URL if needed.

**`flagged` sources with 403/5xx:** The source exists but is temporarily
unavailable or paywalled. Keep the source but note the access issue.

**All sources removed:** If verification removes every source, stop and inform
the user. Do not proceed with empty sources -- gather new ones instead.

## Example Output

```
Source verification (4 sources):
  ✓ https://peps.python.org/pep-0008/ — 200 OK, title matches
  ✓ https://effectivepython.com/ — 200 OK (no title to compare)
  ✗ https://fakeblog.example/post — 404 Not Found (REMOVED)
  ⚠ https://arxiv.org/abs/2509.21361 — Title mismatch —
      cited: "The Maximum Effective Context Window...",
      actual: "Context Is What You Need..." (FLAGGED)

Summary: 2 ok, 1 removed, 1 flagged
```
