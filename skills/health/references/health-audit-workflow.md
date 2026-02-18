# Health Audit Workflow (Tier 1 + Tier 2)

Run deterministic checks plus LLM-assisted quality assessment.

## Steps

1. **Run the health check with tier 2 triggers**
   ```bash
   python3 scripts/check_health.py --root . --tier2
   ```

2. **Review Tier 1 issues** — present structural/deterministic findings

3. **Evaluate Tier 2 triggers** — for each trigger in the output:
   - Read the context dict (document excerpt, section content, etc.)
   - Assess quality based on the trigger's question
   - Report findings with severity and specific suggestions

4. **Present combined results** — T1 issues + T2 assessments
