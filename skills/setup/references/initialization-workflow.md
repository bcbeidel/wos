# Initialization Workflow

Use this workflow when `/context/` does not exist in the project root.

## Steps

1. **Gather information**
   - Ask the user for a brief project purpose (1-2 sentences for the CLAUDE.md header)
   - Ask for 1-3 initial domain areas to create
   - Normalize area names to lowercase-hyphenated format

2. **Run scaffold**
   ```bash
   python3 scripts/run_scaffold.py init --purpose "PURPOSE" --areas "area-one,area-two"
   ```
   This creates the full directory structure with overview templates.

3. **Run discovery**
   ```bash
   python3 scripts/run_discovery.py --root .
   ```
   This generates the CLAUDE.md manifest, AGENTS.md, and rules file.

4. **Present summary**
   Show the user what was created:
   - Directory tree
   - Number of areas initialized
   - Location of CLAUDE.md manifest
   - Next step: use `/wos:curate` to add content

## Error Handling

- If `/context/` already exists, redirect to the add-area workflow
- If scaffold reports skipped files, inform the user which files were preserved
