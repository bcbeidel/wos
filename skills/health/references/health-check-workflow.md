# Health Check Workflow (Tier 1)

Run deterministic validation across all documents.

## Steps

1. **Run the health check script**
   ```bash
   python3 scripts/check_health.py --root . --no-color
   ```

2. **Show the output** directly to the user — the script formats results as
   human-readable text with issues sorted by severity.

3. **If the user wants more detail**, re-run with `--detailed`:
   ```bash
   python3 scripts/check_health.py --root . --detailed --no-color
   ```

4. **Suggest next steps**:
   - If failures exist: recommend specific fixes or `/wos:maintain`
   - If warnings only: suggest reviewing and optionally fixing
   - If clean: congratulate and suggest `/wos:health audit` for deeper check
