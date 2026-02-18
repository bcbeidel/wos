# Maintain Regenerate Workflow

Regenerate discovery artifacts (CLAUDE.md manifest, rules file, AGENTS.md)
to match the current state of files on disk.

## Steps

1. **Show current manifest state**
   - Read CLAUDE.md between the work-os markers
   - Show the current manifest content

2. **Scan disk for actual state**
   ```bash
   python3 scripts/run_discovery.py --root .
   ```
   Discovery scans `/context/`, reads frontmatter, and regenerates:
   - CLAUDE.md manifest (between markers)
   - `.claude/rules/work-os-context.md`
   - AGENTS.md (mirrors CLAUDE.md manifest)

3. **Show what changed**
   - If manifest is already in sync: "Already up to date."
   - If drift detected: show the diff between old and new manifest

4. **Apply with user confirmation**
   - Discovery writes all three files atomically
   - Confirm changes to user

## When to Use

- After adding or removing context documents manually
- When health reports `check_manifest_sync` warning
- After renaming or restructuring areas under `/context/`
- As a periodic maintenance step
