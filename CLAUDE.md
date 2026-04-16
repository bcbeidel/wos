@AGENTS.md

# CLAUDE.md

This repo is **toolkit** — a Claude Code plugin marketplace. You are building
the tools, not using them.

## Build & Test

Install plugin packages and dev dependencies:

```bash
pip install -e plugins/wiki -e plugins/check -e ".[dev]"
```

Run tests:
```bash
python -m pytest plugins/wiki/tests/ plugins/check/tests/ -v
```

Lint:
```bash
ruff check plugins/
```

No runtime dependencies (stdlib only). Dev dependencies in root `pyproject.toml`.

Note: `ruff` may not be installed locally; CI runs it via GitHub Actions.

## Design Principles

1. **Convention over configuration** — document patterns, don't enforce them
2. **Structure in code, quality in skills** — deterministic checks in Python or shell scripts, judgment in LLMs
3. **Single source of truth** — navigation is derived from disk, never hand-curated
4. **Keep it simple** — no frameworks, no unnecessary indirection. Inheritance is acceptable when a document type has distinct data or validation behavior that would otherwise scatter across unrelated modules.
5. **When in doubt, leave it out** — every field, abstraction, and feature must justify itself
6. **Omit needless words** — agent-facing output earns every token
7. **Depend on nothing** — stdlib-only core; scripts isolate their own deps
8. **One obvious way to run** — every script, every skill, same entry point
9. **Separate reads from writes** — audit observes; fixes require explicit action
10. **Bottom line up front** — key insights at top and bottom, detail in the middle

## Architecture

### Marketplace Structure

Five plugins under `plugins/`, each independently installable:

| Plugin | Path | Python package | Skills |
|--------|------|----------------|--------|
| `build` | `plugins/build/` | none | `build-skill`, `build-rule`, `build-hook`, `build-subagent`, `build-refine-prompt` |
| `check` | `plugins/check/` | `check` | `check-skill`, `check-rule`, `check-hook`, `check-subagent`, `check-skill-chain` |
| `wiki` | `plugins/wiki/` | `wiki` | `setup`, `research`, `ingest`, `lint` |
| `work` | `plugins/work/` | none | `scope-work`, `plan-work`, `start-work`, `verify-work`, `finish-work` |
| `consider` | `plugins/consider/` | none | 16 mental models + meta |

Each plugin versions independently from `0.1.0`. A version bump requires updating
the plugin's `pyproject.toml` and `.claude-plugin/plugin.json`. See CONTRIBUTING.md.

### Package Structure

**`plugins/wiki/wiki/`** — importable Python package:
- `document.py` — `Document` base class + subclasses + `parse_document()` factory
- `validators.py` — project-wide orchestration (`validate_project()`); index and project-file checks
- `url_checker.py` — HTTP HEAD/GET URL reachability (urllib)
- `agents_md.py` — marker-based AGENTS.md section management + `replace_marker_section()`
- `wiki.py` — `WikiDocument` subclass + schema parsing + directory-level orphan checks
- `skill_chain.py` — `ChainDocument` subclass + step table parsing + structural validation
- `research.py` — `ResearchDocument` subclass + source URL checks + gate checking
- `plan.py` — `PlanDocument` subclass + task parsing + completion tracking
- `project.py` — thin orchestration wrapper over validators

**`plugins/check/check/`** — importable Python package (standalone for build tooling):
- `document.py` — duplicated from wiki (check must be standalone)
- `url_checker.py` — duplicated from wiki
- `skill.py` — `SkillDocument` + `check_skill_sizes()` + `check_skill_meta()`

**`plugins/wiki/scripts/`** — thin CLI entry points with PEP 723 inline metadata:
- `lint.py` — run validation checks
- `update_preferences.py` — write communication preferences to AGENTS.md

### Document Model

`Document` is the base class. Type-specific subclasses add structured data fields and
override `issues()` for type-specific validation. `parse_document()` is the single
factory — it routes to the right subclass based on frontmatter `type` and file suffix.

```
Document          — common fields + base validation (required frontmatter, related paths)
├── ResearchDocument  — source URL checks, draft marker check, sources required
├── PlanDocument      — tasks field (parsed from content), completion tracking
├── ChainDocument     — steps field (parsed from content), cycle/termination checks
└── WikiDocument      — schema conformance, wiki-specific frontmatter checks
```

Required frontmatter: `name`, `description`
Optional frontmatter: `type` (routes subclass selection), `sources`, `related`, `status`, plus extra fields in `meta`.

**Validation interface** — two methods on every class:
- `doc.issues(root) -> list[dict]` — full issue list, each with `file`, `issue`, `severity`
- `doc.is_valid(root) -> bool` — True if no `fail`-severity issues

Subclasses call `super().issues(root)` and extend. Type-specific checks live on the
subclass — never on the base class.

### Skills

Skill prefix follows plugin name (e.g., `/wiki:setup`, `/work:plan-work`, `/build:build-skill`).
Skills live at `plugins/<plugin>/skills/<name>/SKILL.md`.

### Key Entry Points

- `plugins/wiki/wiki/document.py` — Document dataclass and `parse_document()`
- `plugins/wiki/wiki/validators.py` — `validate_project()` runs all checks
- `plugins/check/check/skill.py` — `check_skill_sizes()` and `check_skill_meta()` for skill quality
- `plugins/wiki/scripts/lint.py` — CLI for validation

## Plans

- Plans MUST be detailed lists of individual tasks
- Plans MUST be stored as markdown in `/docs/plans`
- Plans MUST include checkboxes to indicate progress, marking things off as completed
- Plans MUST indicate the branch, and pull-request associated with the work
- Plans MUST be implemented on a branch, and merged only after human review of a pull-request
- Completed plans are historical records — `wos/` path references in older completed plans are intentional; do not update them

## Conventions

- Python 3.9 — use `from __future__ import annotations` for type hints,
  `Optional[X]` for runtime expressions
- **Script path convention:** Scripts use `Path(__file__).parent.parent` (2 levels)
  to find the plugin root. Per-skill scripts use the appropriate depth to reach
  their plugin root. Each `sys.path` insertion includes a comment with the full
  path chain (e.g., `# plugins/wiki/scripts/ → plugins/wiki/ (plugin root)`).
  Do NOT use marker-based walk-up (`pyproject.toml` search) — it finds the
  user's project root instead of the plugin root.
- **`work` and `build` scripts:** These plugins have no Python package. Their
  per-skill scripts rely on editable installs of `wiki` and `check`. Do not add
  sys.path manipulation to `work`/`build` scripts — the editable install is the contract.
- `doc.issues(root)` returns `list[dict]` with keys: `file`, `issue`, `severity`; `doc.is_valid(root)` returns `bool`
- `ValueError` + stdlib exceptions only (no custom exception hierarchy)
- Tests use inline markdown strings and `tmp_path` fixtures
