---
name: health
description: >
  This skill should be used when the user asks to "check health",
  "validate documents", "run validation", "audit content quality",
  "review documents", "check coverage", "check freshness",
  "run health check", or "what needs attention".
argument-hint: "[check|audit|review|coverage|freshness]"
---

# Health Skill

Observe and report on project content quality. Read-only — reports but
does not modify any files.

## Routing

Route by keyword in the user's request:

| Keyword | Workflow | What it does |
|---------|----------|-------------|
| check / validate | health-check | Tier 1 deterministic validation |
| audit | health-audit | Tier 1 + Tier 2 LLM assessment |
| review | health-review | Full T1+T2+T3 with human Q&A |
| coverage | health-coverage | Gap analysis |
| freshness | health-freshness | Staleness report |

Default (no keyword): run **health-check**.

## Implementation

All validation runs through the CLI script:

```bash
# Tier 1 only (default, CI-friendly)
python3 scripts/check_health.py --root .

# Detailed output with suggestions
python3 scripts/check_health.py --root . --detailed

# Tier 1 + Tier 2 triggers
python3 scripts/check_health.py --root . --tier2

# JSON output for programmatic use
python3 scripts/check_health.py --root . --json
```

Default output is human-readable text. Use `--json` for machine-parseable output.

Exit code: 0 if no `severity: fail`, 1 otherwise.

## Severity Levels

| Severity | Meaning | CI behavior |
|----------|---------|------------|
| `fail` | Must fix — structural or correctness problem | Exit 1 |
| `warn` | Should fix — quality or consistency concern | Exit 0 |
| `info` | Advisory — staleness or minor suggestion | Exit 0 |

## Key Rules

- Health is read-only — use `/wos:maintain` to act on findings
- Research documents are NOT checked for `last_validated` staleness
- Broken `related` file paths are always `severity: fail`
- Related URLs are format-checked only (no HTTP fetch)
- Overview-topic sync mismatches are `severity: fail`
- Empty project exits 0 with a message suggesting `/wos:setup`
