---
document_type: plan
description: "Build the setup skill that initializes new knowledge bases and adds domain areas with correct directory structure and discovery artifacts"
last_updated: 2026-02-17
status: draft
related:
  - 2026-02-17-document-type-models.md
  - 2026-02-17-discovery-layer.md
  - ../research/2026-02-17-skills-architecture-design.md
---

# Build Setup Skill

## Objective

A `/dewey:setup` skill exists that can initialize a new knowledge base from
scratch (scaffold directories, generate config, create CLAUDE.md manifest) and
add new domain areas to an existing knowledge base (create area directory with
overview.md, update manifest). After running setup, the knowledge base is ready
for content creation via the curate skill.

## Context

- Skills architecture: `artifacts/research/2026-02-17-skills-architecture-design.md` §3.2
- Depends on document type models and discovery layer
- Two workflows: `setup-init` (new KB) and `setup-area` (add area)
- Routing: check for `.dewey/config.json` existence

## Steps

1. Create `skills/setup/SKILL.md` with skill description, conversational
   triggers ("set up a knowledge base", "initialize", "add a new area"),
   and routing logic (config exists → area, else → init)

2. Create `skills/setup/workflows/setup-init.md`:
   - Ask user for knowledge base purpose (role persona for AGENTS.md)
   - Ask for initial domain areas (1-3 to start)
   - Run scaffold: create `/context/`, `/artifacts/research/`,
     `/artifacts/plans/`, `.dewey/config.json`
   - For each area: create `context/{area}/overview.md` with template
   - Run discovery to generate CLAUDE.md manifest and rules file
   - Present summary of what was created

3. Create `skills/setup/workflows/setup-area.md`:
   - Ask user for new area name and description
   - Create `context/{area}/overview.md` with template
   - Run discovery to update CLAUDE.md manifest
   - Present summary

4. Create `scripts/scaffold.py`:
   - `scaffold_knowledge_base(root, areas, persona)` — create full directory
     structure, config file, overview templates
   - `scaffold_area(root, area_name, description)` — create single area
   - Uses template functions from document type models for overview content
   - Never overwrites existing files

5. Write tests: scaffold creates expected directory structure, scaffold
   doesn't overwrite existing files, scaffold with 2 areas creates 2
   overview files, config.json written correctly

## Verification

- `/dewey:setup` on a fresh directory creates the full structure
- `.dewey/config.json` exists after init
- CLAUDE.md has knowledge base manifest section with markers
- Each area has an `overview.md` with valid frontmatter
- Running setup-area on existing KB adds area without disturbing existing content
- `python3 -m pytest tests/test_scaffold.py -v` passes
