---
name: create-context
description: >
  This skill should be used when the user asks to "set up wos",
  "initialize project context", "scaffold context directories",
  "create context structure", "add a new area", "add a domain area",
  or "configure wos for this project".
disable-model-invocation: true
argument-hint: "[area-name]"
---

# Create Context Skill

Initialize a new project with structured context or add domain areas to an
existing project.

## Routing

Check whether the project already has a `/context/` directory:

- **No `/context/` directory** -> Run the initialization workflow
  (see `references/initialization-workflow.md`)
- **`/context/` exists** -> Run the add-area workflow
  (see `references/add-area-workflow.md`)

## Quick Reference

**Initialization** creates:
- `context/` directory with one or more area subdirectories
- `artifacts/research/` and `artifacts/plans/` directories
- `_overview.md` in each area (valid overview frontmatter)
- CLAUDE.md with `## Context` manifest (via discovery)
- AGENTS.md mirroring the manifest
- `.claude/rules/wos-context.md` rules file

**Add area** creates:
- `context/{area-name}/` directory
- `_overview.md` with valid overview frontmatter
- Updates CLAUDE.md and AGENTS.md manifests (via discovery)

## Implementation

All scaffolding is done via Python scripts for deterministic output:

```bash
# Initialize a new project
python3 scripts/run_scaffold.py init --purpose "Project description" --areas "area-one,area-two"

# Add an area to an existing project
python3 scripts/run_scaffold.py area --name "area-name" --description "What this area covers"
```

After scaffolding, always run discovery to update manifests:

```bash
python3 scripts/run_discovery.py --root .
```

## Conventions

- Area names are lowercase hyphenated: `python-basics`, `api-design`
- Each area must have an `_overview.md` with valid `overview` frontmatter
- Never overwrite existing files -- skip and report if file already exists
- The `/context/` directory's existence is the initialization signal (no config file)
