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

Lint:
```bash
ruff check wos/ tests/ scripts/
```

Dependencies: `pydantic>=2.0`, `pyyaml>=6.0`, `requests>=2.28` (declared in `pyproject.toml`)

Note: `ruff` may not be installed locally; CI runs it via GitHub Actions.

Version bump requires updating all three: `pyproject.toml`,
`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

## Architecture

### Package Structure

- `wos/` — importable Python package with core logic
  - **Core:** `document_types.py` (models, dispatch tables, `parse_document()`),
    `validators.py` (per-file), `cross_validators.py` (multi-file),
    `templates.py`, `discovery.py`, `scaffold.py`
  - **Extended:** `auto_fix.py`, `token_budget.py`, `tier2_triggers.py`,
    `source_verification.py`
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

### Skills

Prefix: `/wos:` (e.g., `/wos:create-context`, `/wos:audit`). Each skill has
`SKILL.md` (routing) and optionally `references/`.

### Key Separation

- **Audit** is read-only — observes and reports, can run in CI
- **Fix** is write — acts on audit findings, requires approval
- **Create-document / Update-document** — document lifecycle
- **Create-context / Update-context** — project and area scaffolding

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

### Key Entry Points

- `wos/document_types.py` — schema foundation; start here for new document types
- `wos/validators.py` — per-file validators dispatched by `VALIDATORS_BY_TYPE`
- `wos/cross_validators.py` — multi-file validators (link graph, manifest sync, naming)
- `scripts/check_health.py` — CLI that wires validators into `/wos:audit` output

## Reference

- Architecture & design: [2026-02-18-architecture-snapshot.md](artifacts/research/2026-02-18-architecture-snapshot.md)

## Domain Model Conventions

All domain objects in `wos/models/` follow a standard DDD protocol:

- **Value objects** use `ConfigDict(frozen=True)` (immutable, hashable)
- **Construction:** `from_json(cls, dict)`, `from_markdown(cls, str)` where applicable
- **Representations:** `__str__`, `__repr__`, `to_json()`, `to_markdown()` where applicable
- **Validation:** `validate_self(deep=False) -> list[ValidationIssue]`, `is_valid` property.
  `deep=True` enables I/O checks (e.g., URL reachability)
- **Collection:** composites implement `__len__`, `__iter__`, `__contains__`
- **Tokens:** `get_estimated_tokens()` where meaningful
- **Test builders:** `tests/builders.py` provides `make_*(**overrides)` for each type

New domain objects must implement this protocol. Put behavior on domain objects,
not in standalone helper modules.

Design doc: [DDD Domain Model Enrichment](docs/plans/2026-02-20-ddd-domain-model-enrichment-design.md)

## Conventions

- Python 3.9 — use `from __future__ import annotations` for type hints,
  `Optional[X]` for runtime expressions
- CLI scripts handle both `python` and `python3` invocations gracefully
- CLI scripts default to CWD as root; accept `--root` for override
- Both per-file validators (`validators.py`) and cross-validators
  (`cross_validators.py`) return `list[dict]` with keys: file, issue, severity,
  validator, section, suggestion
- All document operations validate via `parse_document()` before writing
- Skills use free-text intake — users describe intent, Claude routes
- Pydantic `ValidationError` + stdlib exceptions only (no custom exception hierarchy)
- Tests use inline markdown strings and `tests/builders.py` for domain object construction

