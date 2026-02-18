---
name: observe
description: Track how project context is used, surface usage patterns, and generate data-driven curation recommendations
argument-hint: "dashboard | recommendations | trends <file-or-area>"
disable-model-invocation: true
---

# Observe

Shows how project context is being used and where to focus curation effort.

## Routing

| If the user says… | Route to |
|---|---|
| "show usage", "what's being read", "analytics", "dashboard", "utilization" | `references/observe-dashboard.md` |
| "recommendations", "what should I update", "suggest", "priorities" | `references/observe-recommendations.md` |
| "trends for X", "how often is X read", "usage history" | `references/observe-trends.md` |

## How It Works

A PostToolUse hook fires on every Read of a `/context/` file, appending to
`.work-os/utilization/log.jsonl`. Over time this builds a usage profile that
powers recommendations.

**Data layer:** `wos/utilization.py` — record, aggregate, purge
**Recommendations:** `wos/recommendations.py` — gated, category-based suggestions
**Hook:** `wos/hook_log_access.py` — silent, never crashes (exit 0)

## Gating

Recommendations require minimum data before activating:
- At least 10 total reads across all files
- At least 14 days of tracking history

Until these thresholds are met, observe reports what data exists and when
recommendations will become available.
