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
uv run python -m pytest tests/ -v
```

Lint:
```bash
ruff check wos/ tests/ scripts/
```

No runtime dependencies (stdlib only). Dev dependencies in `pyproject.toml`.

Note: `ruff` may not be installed locally; CI runs it via GitHub Actions.

Version bump requires updating all three: `pyproject.toml`,
`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

## Architecture

### Package Structure

- `wos/` — importable Python package (9 modules)
  - `frontmatter.py` — custom YAML subset parser (stdlib-only)
  - `document.py` — `Document` dataclass + `parse_document()`
  - `index.py` — `_index.md` generation + sync checking (preamble-preserving)
  - `validators.py` — 5 validation checks with warn/fail severity (frontmatter, content length, URLs, related paths, index sync)
  - `url_checker.py` — HTTP HEAD/GET URL reachability (urllib)
  - `agents_md.py` — marker-based AGENTS.md section management
  - `markers.py` — shared marker-based section replacement
  - `preferences.py` — communication preferences capture
  - `research_protocol.py` — search protocol logging (`SearchEntry`, `SearchProtocol`, formatters)
- `scripts/` — thin CLI entry points with argparse and PEP 723 inline metadata
  - `audit.py` — run validation checks (`--root`, `--no-urls`, `--json`, `--fix`, `--strict`)
  - `reindex.py` — regenerate all `_index.md` files (preamble-preserving)
  - `check_runtime.py` — canary script to validate `uv run` + PEP 723 pipeline
  - `check_url.py` — URL reachability checking via `wos.url_checker`
  - `update_preferences.py` — communication preferences updates
  - `get_version.py` — print plugin version from `plugin.json`
- `skills/` — skill definitions (SKILL.md + references/) auto-discovered by Claude Code
- `tests/` — pytest tests

### Document Model

One `Document` dataclass. No subclasses, no inheritance.

Required frontmatter: `name`, `description`
Optional frontmatter: `type` (semantic tag), `sources` (URLs), `related` (file paths), plus any extra fields.

`type: research` triggers source requirements (sources must be non-empty, URLs verified).

### Navigation

Each directory under `context/` and `artifacts/` has an auto-generated `_index.md`
listing files with descriptions from frontmatter. AGENTS.md contains a WOS-managed
section (between `<!-- wos:begin -->` / `<!-- wos:end -->` markers) with navigation
instructions, areas table, metadata format, and communication preferences.

### Skills

Prefix: `/wos:` (e.g., `/wos:create`, `/wos:audit`). 7 skills:

| Skill | Purpose |
|-------|---------|
| `/wos:create` | Create project context, areas, or documents |
| `/wos:audit` | Validate project health (5 checks + auto-fix) |
| `/wos:research` | SIFT-based research with source verification |
| `/wos:distill` | Convert research artifacts into focused context files |
| `/wos:consider` | Mental models for problem analysis |
| `/wos:report-issue` | File GitHub issues against WOS repo |
| `/wos:preferences` | Capture communication preferences |

### Validation (5 checks, warn/fail severity)

1. **Frontmatter** (fail + warn) — `name`/`description` non-empty, research sources, dict source warnings, context `related` field warnings
2. **Content length** (warn) — context files exceeding 800 words
3. **Source URLs** (fail) — all URLs in `sources` are programmatically reachable
4. **Related paths** (fail) — file paths in `related` frontmatter exist on disk
5. **Index sync** (fail + warn) — `_index.md` matches directory contents, preamble presence

### Key Entry Points

- `wos/document.py` — Document dataclass and `parse_document()`
- `wos/validators.py` — `validate_project()` runs all 5 checks
- `wos/index.py` — `generate_index()` and `check_index_sync()`
- `scripts/audit.py` — CLI for validation
- `scripts/reindex.py` — CLI for index regeneration

## Reference

- Design doc: [Simplification Design](artifacts/plans/2026-02-22-simplification-design.md)
- Design principles: [WOS Design Principles](artifacts/research/2026-02-22-design-principles.md)

## Plans

- Plans MUST be detailed lists of individual tasks
- Plans MUST be stored as markdown in `/artifacts/plans`
- Plans MUST include checkboxes to indicate progress, marking things off as completed
- Plans MUST indicate the branch, and pull-request associated with the work
- Plans MUST be implemented on a branch, and merged only after human review of a pull-request

## Conventions

- Python 3.9 — use `from __future__ import annotations` for type hints,
  `Optional[X]` for runtime expressions
- **Script invocation: `uv run` is the universal pattern.** All scripts in
  `scripts/` have PEP 723 inline metadata. Skills invoke them via
  `uv run <plugin-scripts-dir>/script.py`. The preflight reference at
  `skills/_shared/references/preflight.md` documents the 3-step check
  (uv availability → canary → actual script). No bare `python3 scripts/...`
  invocations in skill docs.
- CLI scripts default to CWD as root; accept `--root` for override
- Scripts use `sys.path` self-insertion for plugin cache compatibility
- Validators return `list[dict]` with keys: `file`, `issue`, `severity`
- Skills use free-text intake — users describe intent, Claude routes
- `ValueError` + stdlib exceptions only (no custom exception hierarchy)
- Tests use inline markdown strings and `tmp_path` fixtures
