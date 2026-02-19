# Note Document Type Design

**Date:** 2026-02-19
**Issue:** #5
**Branch:** `issue/5-note-document-type`

## Problem

WOS has 4 rigid document types (topic, overview, research, plan). Users have
work products that don't fit any of them — decision records, reading notes,
templates, personal docs, recipes. These files currently live outside WOS-managed
directories because health checks would fail on them.

The original issue #5 proposed template scaffolding, but the actual need is
simpler: a generic document type that WOS tolerates anywhere with minimal
frontmatter, without including it in the agent-discoverable manifest.

## Design Decisions

- **New `note` type, not a tolerance mode.** First-class citizen in the type
  system. Works through existing Pydantic models, dispatch tables, and
  validators. No special-casing needed.
- **Minimal frontmatter.** Only `document_type: note` and `description`
  required. No `last_updated`, no `sources`, no `last_validated`.
  `NoteFrontmatter` does not extend `FrontmatterBase` (which requires
  `last_updated`).
- **No required sections.** Empty sections list in dispatch table. No section
  presence, ordering, or size checks.
- **No directory constraints.** No entry in `DIRECTORY_PATTERNS`. Notes can
  live anywhere.
- **Not in manifest.** Discovery skips `note` type. The agent won't find
  notes proactively.
- **Link validation still applies.** If a note has `related` links, broken
  links are still caught by `check_link_graph`.

## Changes

### 1. document_types.py — Schema

- Add `NOTE = "note"` to `DocumentType` enum
- Add `NoteFrontmatter` model (standalone, not extending `FrontmatterBase`):
  - `document_type: Literal["note"]`
  - `description: str` (min_length=10)
  - Optional: `tags`, `related` (same validation as other types)
- Add `NoteFrontmatter` to the `Frontmatter` discriminated union
- Add dispatch table entries:
  - `SECTIONS[NOTE]` = `[]`
  - `SIZE_BOUNDS[NOTE]` = `SizeBounds(min_lines=1)`
  - `OPTIONAL_SECTIONS[NOTE]` = `{}`
  - No entry in `DIRECTORY_PATTERNS` or `DATE_PREFIX_TYPES`
  - Not added to `CONTEXT_TYPES`, `ARTIFACT_TYPES`, `SOURCE_GROUNDED_TYPES`,
    or `FRESHNESS_TRACKED_TYPES`

### 2. validators.py — Minimal Validation

- `VALIDATORS_BY_TYPE[NOTE]` = `[check_title_heading]`
- Only checks that an H1 title exists. No section, size, staleness, or
  source checks.

### 3. cross_validators.py — Skip Notes Where Appropriate

- `check_link_graph`: Still validates `related` links on notes (if present)
- `check_overview_topic_sync`: Already scoped to topics — no change needed
- `check_manifest_sync`: Already scoped to context types — no change needed
- `check_naming_conventions`: Skip notes (no naming convention enforced)

### 4. discovery.py — Exclude Notes from Manifest

- Discovery already filters by `CONTEXT_TYPES`. Since `NOTE` is not in
  `CONTEXT_TYPES`, notes are automatically excluded. Verify this is the case.

### 5. templates.py — Minimal Render Function

- Add `render_note()`: generates frontmatter + title, no sections
- Add to `TEMPLATES` dispatch table

### 6. auto_fix.py — No Fixes for Notes

- No auto-fix entries needed. Notes have no structural requirements to fix.

## Files Changed

| File | Change |
|---|---|
| `wos/document_types.py` | New enum value, model, dispatch table entries |
| `wos/validators.py` | Minimal validator list for note type |
| `wos/cross_validators.py` | Verify notes are skipped where appropriate |
| `wos/templates.py` | `render_note()` function |
| `tests/test_document_types.py` | Note parsing, dispatch table coverage |
| `tests/test_validators.py` | Note validation (minimal checks pass) |
| `tests/test_templates.py` | Note template round-trip |

## Scope

- One new document type added to existing architecture
- No new files — all changes in existing modules
- No skill changes needed
- No CLI changes needed
- Backward compatible — existing documents unaffected

## Non-Goals

- Does not add custom/user-defined document types
- Does not add note-specific validators beyond title check
- Does not include notes in the CLAUDE.md manifest
- Does not scaffold note directories in `/wos:setup`
