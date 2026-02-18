---
name: observe-recommendations
description: Generate and present data-driven curation recommendations
---

# Observe Recommendations

## Steps

1. **Run the recommendations engine**
   ```python
   from wos.recommendations import generate_recommendations
   result = generate_recommendations(root)
   ```

2. **If gated (insufficient data)**
   The result contains `"skipped"` with the reason. Tell the user:
   - How much data exists now (reads, days)
   - What thresholds must be met (10 reads, 14 days)
   - When to try again (rough estimate based on current pace)

3. **If sufficient data — present recommendations by category**
   Group by category in priority order:
   1. **stale_high_use** — Read frequently but not validated recently.
      Action: prioritize refreshing.
   2. **never_referenced** — Zero reads after sufficient tracking.
      Action: check if linked and discoverable.
   3. **hot_area** — Area with disproportionately high reads.
      Action: may need more topics or better organization.
   4. **cold_area** — Area with very few reads.
      Action: may be out of scope or poorly linked.
   5. **low_utilization** — Read far below median.
      Action: improve discoverability or relevance.

4. **For each recommendation show:**
   - File or area path
   - Category label
   - Reason (data-driven explanation)
   - Suggested action

5. **Present summary stats**
   From `result["summary"]`: total reads, tracking days, files tracked,
   context files, recommendation count.

6. **Offer next steps**
   - "Want me to fix stale content?" → route to `/wos:maintain`
   - "Want me to add content for a hot area?" → route to `/wos:curate`
   - "Want to see trends for a specific file?" → route to observe-trends
