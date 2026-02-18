# CLAUDE.md

This repo is **work-os** — a Claude Code plugin for building and maintaining
structured knowledge bases. You are helping build this tooling.

## What This Repo Is

Work-os is a plugin (not a knowledge base itself). It provides skills, scripts,
and agents that help users create, validate, and maintain knowledge bases in
their own repos. When working in this repo, you are building the tool, not
using it.

## Build & Test

```bash
python3 -m pytest tests/ -v
```

One dependency: `pydantic>=2.0`

## Architecture

### Schema-First Design

Everything derives from the Pydantic document type models in
`scripts/document_types.py`. The models define four document types (topic,
overview, research, plan) and dispatch tables that control templates, validators,
sections, size bounds, and directory patterns.

**Adding a new document type:** Add a model, add dispatch table entries. No
skill routing changes needed.

### Skills (build order)

| Phase | Skills |
|-------|--------|
| Foundation | Document type models, discovery layer |
| Core | setup, curate, health, maintain, report-issue |
| Capability | research, consider |
| Extended | import, observe, history, connect, teach |

Each skill has: `SKILL.md` (routing), `workflows/` (multi-step processes),
optionally `references/` (domain knowledge) and `scripts/` (Python helpers).

### Key Separation

- **Health** is read-only — observes and reports, can run in CI
- **Maintain** is write — acts on health signals, requires approval
- **Curate** handles content lifecycle — create, ingest, propose, promote
- **Setup** runs once (or rarely) — scaffold and configure

### Document Types

| Type | Location | Purpose |
|------|----------|---------|
| `topic` | `/context/{area}/{topic}.md` | Actionable guidance with citations |
| `overview` | `/context/{area}/overview.md` | Area orientation and topic index |
| `research` | `/artifacts/research/{date}-{slug}.md` | Investigation snapshot |
| `plan` | `/artifacts/plans/{date}-{slug}.md` | Actionable work plan |

Context types (topic, overview) are agent-facing — they appear in the CLAUDE.md
manifest. Artifact types (research, plan) are internal work products, reachable
via `related` links.

## Implementation Plans

Plans in `artifacts/plans/` define what to build. Each plan follows the plan
document type format: Objective, Context, Steps, Verification.

Current plans (all draft):
- Document type models (foundation)
- Discovery layer (foundation)
- Setup, curate, health, maintain, report-issue (core skills)
- Research, consider (capability skills)

## Design Documents

Full design docs are in `artifacts/research/`:
- `2026-02-16-document-type-reference.md` — concise rules
- `2026-02-16-document-type-specification.md` — normative spec
- `2026-02-16-document-type-data-models.md` — Pydantic models
- `2026-02-17-skills-architecture-design.md` — skills architecture

## Conventions

- Python 3.9 — use `from __future__ import annotations` for type hints,
  `Optional[X]` for runtime expressions
- Scripts must be runnable standalone (`if __name__ == "__main__"` with argparse)
- Validators and triggers always return `list[dict]`
- All document operations validate via `parse_document()` before writing
- Skills use free-text intake — users describe intent, Claude routes

## Design Principles

18 principles in three layers — see
[Design Principles](artifacts/research/2026-02-17-design-principles.md):

1. **Knowledge amplifier** (5 principles): source primacy, dual audience,
   domain-shaped organization, right-sized scope, progressive disclosure
2. **Agent operating system** (5 principles): schema-first design, separation
   of observation/action, convention over configuration, derived artifacts,
   free-text intake
3. **Quality-first workflow** (5 principles): SIFT at the source, structured
   reasoning before action, three-tier validation, empirical feedback,
   provenance and traceability
4. **Cognitive science** (3 principles): explain the why, concrete before
   abstract, multiple representations
