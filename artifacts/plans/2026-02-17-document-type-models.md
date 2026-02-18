---
document_type: plan
description: "Implement Pydantic v2 document type models, dispatch tables, and parse/validate functions that serve as the shared foundation for all skills"
last_updated: 2026-02-17
status: draft
related:
  - ../research/2026-02-16-document-type-data-models.md
  - ../research/2026-02-16-document-type-specification.md
---

# Implement Document Type Models

## Objective

A Python module exists at `scripts/document_types.py` that provides Pydantic v2
models for all four document types (topic, overview, research, plan), dispatch
tables for sections/size/validators/directory patterns, and a `parse_document()`
function that takes a file path and returns a validated `Document` instance or
raises `ValidationError` with clear messages.

Any skill or script can `import document_types` and get type-safe document
handling with zero knowledge of type-specific rules.

## Context

- Data model design: `artifacts/research/2026-02-16-document-type-data-models.md`
- Normative spec: `artifacts/research/2026-02-16-document-type-specification.md`
- Requires `pydantic>=2.0` (already in `requirements.txt`)
- Python 3.9 runtime — use `from __future__ import annotations` for type hints,
  `Optional[X]` for runtime expressions

## Steps

1. Create `scripts/document_types.py` with the `DocumentType` and `PlanStatus`
   enums, type grouping constants (`CONTEXT_TYPES`, `ARTIFACT_TYPES`,
   `SOURCE_GROUNDED_TYPES`, `FRESHNESS_TRACKED_TYPES`)

2. Implement shared models: `Source` (url + title) and `FrontmatterBase`
   (description with min-length and word-count validators, last_updated with
   future-date check, optional tags and related)

3. Implement type-specific frontmatter models: `TopicFrontmatter`,
   `OverviewFrontmatter`, `ResearchFrontmatter`, `PlanFrontmatter` — each with
   a `Literal` document_type field and type-specific required/optional fields

4. Create the discriminated union:
   `Frontmatter = Annotated[Union[...], Field(discriminator="document_type")]`

5. Implement dispatch tables: `SECTIONS` (with `SectionSpec` model),
   `OPTIONAL_SECTIONS`, `SIZE_BOUNDS` (with `SizeBounds` model),
   `DIRECTORY_PATTERNS`

6. Implement `_split_markdown(content)` — parse YAML frontmatter, extract title
   from first H1, extract sections from H2 headings, return raw content

7. Implement `Document` model with properties: `document_type`, `required_sections`,
   `size_bounds`

8. Implement `parse_document(path, content)` — split markdown, validate
   frontmatter via discriminated union, return `Document`

9. Write tests: valid documents for each type pass, missing required fields fail
   with clear messages, wrong directory patterns detected, future dates rejected,
   description-too-short rejected, discriminated union routes correctly

## Verification

- `python3 -c "from document_types import parse_document, DocumentType"` succeeds
- `python3 -m pytest tests/test_document_types.py -v` — all tests pass
- A topic document with missing `sources` raises `ValidationError` mentioning "sources"
- A plan document with `status: "invalid"` raises `ValidationError` mentioning "status"
- A research document parses successfully without `last_validated` (not required for research)
- `parse_document()` on a real markdown string returns a `Document` with correct type
