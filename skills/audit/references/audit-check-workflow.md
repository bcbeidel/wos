# Audit Check Workflow (Tier 1)

Run deterministic validation across all documents.

## Steps

1. **Run the health check script**
   ```bash
   python3 scripts/check_health.py --root .
   ```

2. **Parse the JSON output** — group issues by severity

3. **Present results** to the user:
   - Count of files checked
   - Issues grouped by severity (fail first, then warn, then info)
   - For each issue: file path, validator name, description, suggestion

4. **Suggest next steps**:
   - If failures exist: recommend specific fixes or `/wos:fix`
   - If warnings only: suggest reviewing and optionally fixing
   - If clean: congratulate and suggest `/wos:audit audit` for deeper check
