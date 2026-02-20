# Health Freshness Workflow

Report on document staleness based on `last_validated` dates.

## Thresholds

| Age | Severity | Label |
|-----|----------|-------|
| 30+ days | info | Getting stale |
| 60+ days | warn | Needs attention |
| 90+ days | stale | Overdue for review |

## Steps

1. **Run the health check script**
   ```bash
   python3 scripts/check_health.py --root .
   ```

2. **Filter issues** to only staleness-related findings
   (validator: `check_last_validated`)

3. **Group by urgency** — 90+ days first, then 60+, then 30+

4. **Present report** with suggested review priorities
