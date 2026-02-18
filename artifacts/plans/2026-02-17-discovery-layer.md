---
document_type: plan
description: "Implement the discovery layer that auto-generates CLAUDE.md manifest sections and rules files from knowledge base contents on disk"
last_updated: 2026-02-17
status: draft
related:
  - 2026-02-17-document-type-models.md
  - ../research/2026-02-17-skills-architecture-design.md
---

# Implement Discovery Layer

## Objective

A Python module exists at `scripts/discovery.py` that scans a knowledge base
directory, reads frontmatter from context documents (topics + overviews), and
generates two outputs: a CLAUDE.md manifest section (markdown between markers)
and a rules file (`.claude/rules/dewey-knowledge-base.md`). Both are
regenerated deterministically from disk state.

Running `python3 scripts/discovery.py --knowledge-base-root /path/to/kb`
produces correct, current discovery artifacts every time.

## Context

- Discovery layer design: `artifacts/research/2026-02-17-skills-architecture-design.md` §2
- Depends on document type models for frontmatter parsing
- CLAUDE.md manifest is context-types only (topics + overviews)
- Artifacts (research, plans) are not in the manifest
- Marker format: `<!-- dewey:knowledge-base:begin -->` / `<!-- dewey:knowledge-base:end -->`

## Steps

1. Implement `scan_knowledge_base(root, knowledge_dir)` — walk the `/context/`
   directory, parse frontmatter from each `.md` file using `parse_document()`,
   return structured data: list of areas, each with overview metadata and list
   of topic metadata (path, title, description)

2. Implement `render_manifest(areas)` — generate the markdown manifest section:
   one H3 per area, overview link, topic table with Description column.
   Output is the content between markers (not including markers themselves)

3. Implement `update_claude_md(file_path, manifest_content)` — read existing
   CLAUDE.md, find markers, replace content between them. If no markers exist,
   append markers + content. If file doesn't exist, create it with markers

4. Implement `render_rules_file()` — generate the rules file content: document
   types, directory layout, frontmatter requirements, when to create each type,
   how to use `related` links. Under 50 lines, actionable only

5. Implement `update_rules_file(rules_dir, content)` — write to
   `.claude/rules/dewey-knowledge-base.md`, creating directory if needed

6. Wire CLI: `python3 scripts/discovery.py --knowledge-base-root ROOT` runs
   scan → render manifest → update CLAUDE.md → render rules → update rules file

7. Implement `update_agents_md(file_path, manifest_content)` — same marker
   logic as CLAUDE.md, mirrored content for AGENTS.md

8. Write tests: empty knowledge base produces empty manifest, single area
   with topics produces correct table, user content outside markers preserved,
   markers added to existing file without markers, rules file content is
   under 50 lines

## Verification

- `python3 scripts/discovery.py --knowledge-base-root /path/to/test-kb` produces
  a CLAUDE.md with correct manifest section
- Existing content outside markers in CLAUDE.md is preserved after regeneration
- Rules file at `.claude/rules/dewey-knowledge-base.md` exists and is under 50 lines
- Running discovery twice produces identical output (idempotent)
- AGENTS.md contains the same manifest content as CLAUDE.md
