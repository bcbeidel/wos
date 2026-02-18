---
document_type: plan
description: "Build the curate skill for creating, updating, ingesting, proposing, and promoting documents across all four types"
last_updated: 2026-02-17
status: draft
related:
  - 2026-02-17-document-type-models.md
  - 2026-02-17-discovery-layer.md
  - 2026-02-17-skill-setup.md
  - ../research/2026-02-17-skills-architecture-design.md
---

# Build Curate Skill

## Objective

A `/dewey:curate` skill exists that handles all content lifecycle operations:
creating documents of any type, ingesting content from URLs, proposing drafts
for review, promoting proposals, and updating existing documents. The skill
uses free-text intent classification — users describe what they want and Claude
routes to the correct workflow. Document type dispatch happens via the Pydantic
models and dispatch tables, not type-specific branching.

## Context

- Skills architecture: `artifacts/research/2026-02-17-skills-architecture-design.md` §3.2
- Depends on document type models (templates, frontmatter validation)
- Depends on discovery layer (manifest regeneration after content changes)
- Depends on setup (knowledge base must exist)
- Free-text routing: "investigate X" → research, "plan how to Y" → plan,
  "add topic about Z" → topic, "update overview" → overview update

## Steps

1. Create `skills/curate/SKILL.md` with skill description, broad
   conversational triggers ("add", "create", "research", "plan", "ingest",
   "propose", "update", "save this to my knowledge base"), and routing logic:
   - No knowledge base → redirect to setup
   - Classify intent → route to workflow
   - Intent classification: detect document type from user language

2. Create `skills/curate/workflows/curate-add.md`:
   - Determine document type from user intent
   - For context types (topic, overview): resolve target area, verify it exists
   - For artifact types (research, plan): generate date-prefixed filename
   - Research sources (for topic/research types): gather 5-7 candidates,
     evaluate using source hierarchy
   - Draft content using type-specific template from dispatch tables
   - Validate via `parse_document()` before writing
   - Run discovery to update manifest (if context type)
   - Present draft for user review

3. Create `skills/curate/workflows/curate-ingest.md`:
   - Fetch URL content
   - Evaluate source quality (authority, freshness, relevance)
   - Determine whether content maps to an existing topic or a new one
   - Draft document with source properly cited
   - Validate and present for review

4. Create `skills/curate/workflows/curate-propose.md`:
   - Write draft to `_proposals/` staging directory
   - Include rationale and target location in proposal metadata
   - Validate proposal has complete frontmatter

5. Create `skills/curate/workflows/curate-promote.md`:
   - Read proposal from `_proposals/`
   - Validate via health check
   - Move to target location
   - Update manifest
   - Remove proposal file

6. Create `skills/curate/workflows/curate-update.md`:
   - Read existing document via `parse_document()`
   - Apply updates (preserve existing frontmatter, update `last_updated`)
   - Re-validate via `parse_document()` before writing
   - Update manifest if description changed

7. Create `scripts/templates.py`:
   - One render function per document type: `render_topic()`,
     `render_overview()`, `render_research()`, `render_plan()`
   - `TEMPLATES` dispatch table keyed by `DocumentType`
   - Each function generates valid markdown with correct frontmatter and
     section headings from `SECTIONS` table
   - Output passes `parse_document()` validation

8. Write tests: templates produce valid documents for each type,
   `parse_document(render_topic(...))` round-trips successfully,
   intent classification maps common phrases to correct types

## Verification

- "I want to investigate X" routes to research document creation
- "Add a topic about Y" routes to topic creation in correct area
- "Let's plan how to Z" routes to plan creation in `/artifacts/plans/`
- Created documents pass `parse_document()` validation
- CLAUDE.md manifest updates after topic creation
- Manifest does NOT update after research/plan creation (artifacts not in manifest)
- Templates for all 4 types produce valid output
- `python3 -m pytest tests/test_templates.py -v` passes
