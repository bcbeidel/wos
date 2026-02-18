---
name: observe-trends
description: Show read count trends for a specific file or area
---

# Observe Trends

## Steps

1. **Identify target**
   User specifies a file path or area name. If ambiguous, ask for clarification.

2. **Load timeseries data**
   ```python
   from wos.utilization import read_utilization_timeseries, read_utilization
   entries = read_utilization_timeseries(root, file_path)
   ```
   For an area, load all files under `context/{area}/` and combine entries.

3. **Bucket by week**
   Group entries into weekly buckets (Monday–Sunday). Show:
   - Week start date
   - Read count for that week
   - Running total

4. **Compare against project average**
   ```python
   stats = read_utilization(root)
   ```
   Calculate average reads per file. Show how this file/area compares:
   - Above average, at average, or below average
   - Ratio (e.g., "2.3x the project average")

5. **Note inflection points**
   Look for weeks where reads changed significantly (>2x previous week
   or dropped to zero). These may indicate:
   - New team member onboarding (sudden spike)
   - Content becoming outdated (gradual decline)
   - Project phase change (area goes hot/cold)

6. **Present as timeline**
   Show weekly data in a compact format. If data is sparse, note that
   trends become more meaningful with more tracking history.
