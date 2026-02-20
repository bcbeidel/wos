# Add Area Workflow

Use this workflow when `/context/` already exists in the project root.

## Steps

1. **Gather information**
   - Ask the user for the new area name
   - Ask for a brief description of what this area covers
   - Normalize the area name to lowercase-hyphenated format

2. **Run scaffold**
   ```bash
   python3 scripts/run_scaffold.py area --name "area-name" --description "What this area covers"
   ```
   This creates the area directory with an `_overview.md` template.

3. **Run discovery**
   ```bash
   python3 scripts/run_discovery.py --root .
   ```
   This updates the CLAUDE.md and AGENTS.md manifests with the new area.

4. **Present summary**
   Show the user:
   - New area directory location
   - Overview file created
   - Updated manifest
   - Next step: use `/wos:create-document` to add topics to this area

## Error Handling

- If the area already exists, inform the user and suggest updating the
  existing `_overview.md` instead
- If the area name contains invalid characters, show the normalized version
  and confirm before proceeding
