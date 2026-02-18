---
name: observe-dashboard
description: Present utilization summary and per-area breakdown
---

# Observe Dashboard

## Steps

1. **Load utilization data**
   ```python
   from wos.utilization import read_utilization, tracking_days, tracking_start_date
   stats = read_utilization(root)
   ```

2. **Present summary**
   - Total reads across all files
   - Unique files tracked
   - Tracking period (start date → today, N days)
   - If no data: explain that the PostToolUse hook logs reads automatically
     and data will accumulate over normal usage

3. **Top 10 most-read files**
   Sort by `read_count` descending. Show file path and count.

4. **Per-area breakdown**
   Group files by area (`context/{area}/...`):
   - Area name
   - Total reads in area
   - Number of topics
   - Average reads per topic

5. **Highlight anomalies**
   Flag any files that are:
   - Read 50+ times with `last_validated` > 90 days (stale high use)
   - Never referenced after 14+ days of tracking

6. **Format as readable table or summary**
   Present in markdown. Keep it scannable — this is a status check, not a report.
