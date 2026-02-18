# Maintain Fix Workflow

Apply safe auto-corrections to health issues found by `/wos:health`.

## Steps

1. **Run health check** to identify fixable issues
   ```bash
   python3 scripts/check_health.py --root .
   ```

2. **Categorize issues** by fixability:
   - **Auto-fixable:** section ordering, missing sections (adds TODO placeholder)
   - **Needs human review:** content quality, broken links, naming issues

3. **Show proposed changes** for each fixable issue:
   - Run auto-fix in dry-run mode:
     ```bash
     python3 scripts/run_auto_fix.py --root . --dry-run
     ```
   - Present a summary: which files, what changes, how many fixes

4. **Get user confirmation** before applying

5. **Apply fixes**
   ```bash
   python3 scripts/run_auto_fix.py --root .
   ```

6. **Re-validate** fixed documents pass `parse_document()`

7. **Report results:**
   - Number of files fixed
   - Remaining issues that need manual attention
   - Suggest next steps for non-auto-fixable issues

## Auto-Fixable Issue Types

| Validator | Fix | Safety |
|-----------|-----|--------|
| `check_section_ordering` | Reorder sections to canonical order | Safe |
| `check_section_presence` | Add missing section with TODO placeholder | Safe |

## Not Auto-Fixable (report only)

- Broken `related` links (need human to decide correct path)
- Content quality issues (need human review)
- Size violations (need human to add/remove content)
- Naming convention issues (need human to choose correct names)
