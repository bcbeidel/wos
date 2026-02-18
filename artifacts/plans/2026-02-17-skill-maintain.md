---
document_type: plan
description: "Build the maintain skill for auto-fixing health issues, managing document lifecycle transitions, regenerating discovery artifacts, and cleaning up the knowledge base"
last_updated: 2026-02-17
status: draft
related:
  - 2026-02-17-skill-health.md
  - 2026-02-17-discovery-layer.md
  - ../research/2026-02-17-skills-architecture-design.md
---

# Build Maintain Skill

## Objective

A `/dewey:maintain` skill exists that acts on health signals by modifying the
knowledge base. It handles four operations: auto-fixing common issues,
transitioning document lifecycle status, regenerating discovery artifacts
(CLAUDE.md manifest and rules file), and cleaning up orphaned content.

Health observes; maintain acts. This separation enables health to run read-only
in CI while maintain requires human approval for write operations.

## Context

- Skills architecture: `artifacts/research/2026-02-17-skills-architecture-design.md` §3.2
- Depends on health (reads health reports to determine what to fix)
- Depends on discovery layer (regenerate operation)
- Depends on document type models (validate after fixes)

## Steps

1. Create `skills/maintain/SKILL.md` with skill description, conversational
   triggers ("fix issues", "update status", "regenerate manifest", "clean up"),
   and routing by action keyword

2. Create `skills/maintain/workflows/maintain-fix.md`:
   - Run health check to identify fixable issues
   - Categorize: auto-fixable vs. needs human review
   - Auto-fixable: missing `last_updated` (set to today), section ordering
     (reorder), missing sections (add empty with TODO), frontmatter formatting
   - Apply fixes, re-validate via `parse_document()`
   - Present summary of changes for approval before writing

3. Create `skills/maintain/workflows/maintain-lifecycle.md`:
   - List documents with `status` field (plans, optionally research)
   - Show current status and last_updated date
   - User selects document and new status
   - Validate transition (e.g., can't go from `complete` back to `draft`
     without explicit override)
   - Update frontmatter, set `last_updated` to today

4. Create `skills/maintain/workflows/maintain-regenerate.md`:
   - Run discovery scan
   - Show diff between current CLAUDE.md manifest and regenerated version
   - Apply update with user confirmation

5. Create `skills/maintain/workflows/maintain-cleanup.md`:
   - Identify orphaned files (in knowledge base dir but not parseable)
   - Identify dead internal links
   - Identify empty proposals older than configurable threshold
   - Present cleanup candidates
   - Execute with user confirmation

6. Implement `scripts/auto_fix.py`:
   - `AUTO_FIXES` dispatch table keyed by issue type
   - Each fix function takes a file path and issue dict, returns modified content
   - All fixes re-validate via `parse_document()` after application
   - Dry-run mode that shows what would change

7. Write tests: auto-fix corrects known issues, auto-fix doesn't corrupt
   valid documents, lifecycle transitions update status correctly,
   cleanup identifies orphaned files

## Verification

- `maintain-fix` on a document with wrong section order produces correctly
  ordered output
- Fixed documents pass `parse_document()` validation
- `maintain-lifecycle` updates plan status from `active` to `complete` and
  sets `last_updated`
- `maintain-regenerate` updates CLAUDE.md manifest to match disk state
- `maintain-cleanup` identifies files that fail `parse_document()`
- All maintain operations require user confirmation before writing
- `python3 -m pytest tests/test_auto_fix.py -v` passes
