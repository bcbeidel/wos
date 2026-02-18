# CLAUDE.md

This repo is **wos** — a Claude Code plugin for building and maintaining
structured project context. You are helping build this tooling.

## What This Repo Is

WOS is a plugin (not a project context itself). It provides skills, scripts,
and agents that help users create, validate, and maintain structured context in
their own repos. When working in this repo, you are building the tool, not
using it.

## Build & Test

```bash
python3 -m pytest tests/ -v
```

One dependency: `pydantic>=2.0` (declared in `pyproject.toml`)

## Architecture

### Package Structure

- `wos/` — importable Python package with core logic (models, discovery,
  validators, templates, etc.)
- `scripts/` — thin CLI entry points with argparse that import from `wos`
- `skills/` — skill definitions (SKILL.md + workflows/) auto-discovered by
  Claude Code
- `tests/` — pytest tests using inline markdown strings

### Schema-First Design

Everything derives from the Pydantic document type models in
`wos/document_types.py`. The models define four document types (topic,
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
| Extended | observe |

Skill prefix: `/wos:` (e.g., `/wos:setup`, `/wos:health`, `/wos:curate`)

Each skill has: `SKILL.md` (routing), `workflows/` (multi-step processes),
optionally `references/` (domain knowledge).

### Key Separation

- **Health** is read-only — observes and reports, can run in CI
- **Maintain** is write — acts on health signals, requires approval
- **Curate** handles content lifecycle — create, ingest, update
- **Setup** runs once (or rarely) — scaffold and configure

### Document Types

| Type | Location | Purpose |
|------|----------|---------|
| `topic` | `/context/{area}/{topic}.md` | Actionable guidance with citations |
| `overview` | `/context/{area}/_overview.md` | Area orientation and topic index |
| `research` | `/artifacts/research/{date}-{slug}.md` | Investigation snapshot |
| `plan` | `/artifacts/plans/{date}-{slug}.md` | Actionable work plan |

Context types (topic, overview) are agent-facing — they appear in the CLAUDE.md
manifest under `## Context`. Artifact types (research, plan) are internal work
products, reachable via `related` links.

## Implementation Plans

Plans in `artifacts/plans/v0.1-foundation/` define what to build. Each plan follows the plan
document type format: Objective, Context, Steps, Verification. The
[roadmap](artifacts/plans/v0.1-foundation/_roadmap.md) tracks build order and status.

Current plans (all draft):
- Document type models (foundation)
- Discovery layer (foundation)
- Setup, curate, health, maintain, report-issue (core skills)
- Research, consider (capability skills)
- Observe (extended)

## Design Documents

Full design docs are in `artifacts/research/v0.1-foundation/`:
- `2026-02-16-document-type-reference.md` — concise rules
- `2026-02-16-document-type-specification.md` — normative spec
- `2026-02-16-document-type-data-models.md` — Pydantic models
- `2026-02-17-skills-architecture-design.md` — skills architecture

## Conventions

- Python 3.9 — use `from __future__ import annotations` for type hints,
  `Optional[X]` for runtime expressions
- CLI scripts handle both `python` and `python3` invocations gracefully
- CLI scripts default to CWD as root; accept `--root` for override
- Validators return `list[dict]` with keys: file, issue, severity, validator,
  section, suggestion
- All document operations validate via `parse_document()` before writing
- Skills use free-text intake — users describe intent, Claude routes
- Pydantic `ValidationError` + stdlib exceptions only (no custom exception hierarchy)
- Tests use inline markdown strings (no fixture files)

## Design Principles

18 principles in three layers — see
[Design Principles](artifacts/research/v0.1-foundation/2026-02-17-design-principles.md):

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
