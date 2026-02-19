# Health Audit Workflow (Tier 1 + Tier 2)

Run deterministic checks plus LLM-assisted quality assessment.

## Steps

1. **Run the health check with tier 2 triggers**
   ```bash
   python3 scripts/check_health.py --root . --tier2 --json
   ```

2. **Show Tier 1 issues** — run the text formatter for human-readable output:
   ```bash
   python3 scripts/check_health.py --root . --detailed --no-color
   ```

3. **Evaluate Tier 2 triggers** — parse the JSON output's `triggers` list.
   For each trigger:
   - Read the context dict (document excerpt, section content, etc.)
   - Assess quality based on the trigger's question
   - Report findings with severity and specific suggestions

4. **Present combined results** — T1 text output + T2 assessments
