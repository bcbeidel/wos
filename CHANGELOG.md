# Changelog

All notable changes to wos will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-02-23

### Removed

- `wos/source_verification.py` and `tests/test_source_verification.py` — 1,021
  lines of dead code. Module was unused by any production import and duplicated
  `url_checker.py`. Research skill references updated to use `url_checker`.

### Added

- `wos/markers.py` — shared `replace_marker_section()` utility extracted from
  duplicated logic in `agents_md.py` and `preferences.py`.
- `tests/test_version.py` — version consistency test asserting `pyproject.toml`,
  `plugin.json`, and `marketplace.json` all have matching versions.

### Changed

- `wos/index.py` now uses `document.parse_document()` for frontmatter extraction
  instead of its own independent YAML parsing.
- Renamed `check_urls` parameter to `verify_urls` in `validators.py` to avoid
  shadowing the imported `check_urls` function from `url_checker.py`.
- `/wos:report-issue` skill simplified from 6 phases to 4. Merged Classify into
  Gather Context, merged Preview into Draft. Trimmed feature request template
  (removed Evaluation, Alternatives Considered, Why This Matters sections).

## [0.2.0] - 2026-02-22

### Changed

- **Architecture simplification.** Replaced 23-class DDD hierarchy with a
  single `Document` dataclass. Reduced 18 validators to 5 essential checks.
  Merged 11 skills into 6. Replaced hand-curated `_overview.md` with
  auto-generated `_index.md`. Net: +2,239 / -14,000 lines.
  ([#38](https://github.com/bcbeidel/wos/pull/38))

### Removed

- `wos/models/` directory (23 classes, DDD hierarchy)
- `wos/cross_validators.py`, `wos/templates.py`, `wos/auto_fix.py`,
  `wos/token_budget.py`, `wos/discovery.py`, `wos/scaffold.py`,
  `wos/document_types.py`, `wos/formatting.py`
- Skills: `create-context`, `create-document`, `discover`, `fix`,
  `update-context`, `update-document`, `health`, `observe`
- Document type subclasses, section ordering validation, size bounds,
  staleness tracking, auto-fix engine, token budget estimation
- Old `scripts/check_health.py`, `scripts/scan_context.py`,
  `scripts/create_document.py`, `scripts/update_discovery.py`,
  `scripts/create_context.py`

### Added

- `wos/document.py` — single `Document` dataclass + `parse_document()`
- `wos/index.py` — `_index.md` generation + sync checking
- `wos/validators.py` — 5 validation checks (frontmatter, research sources,
  URLs, related paths, index sync)
- `wos/url_checker.py` — HTTP HEAD/GET URL reachability
- `wos/agents_md.py` — marker-based AGENTS.md section management
- `scripts/audit.py` — CLI for validation with `--fix` for index regeneration
- `scripts/reindex.py` — CLI for `_index.md` regeneration
- `/wos:create` — unified skill (replaces create-context + create-document)
- `/wos:audit` — rewritten to use 5-check system

## [0.1.9] - 2026-02-20

### Added

- **Communication preferences** (`wos/preferences.py`): Capture user
  communication preferences via five evidence-based dimensions (directness,
  verbosity, depth, expertise, tone) and write them as structured LLM
  instructions in CLAUDE.md using `<!-- wos:communication:begin/end -->`
  markers. New `/wos:preferences` skill with freeform capture workflow.
  Optional preferences step added to `/wos:create-context` initialization.
  ([#22](https://github.com/bcbeidel/wos/issues/22))
- **Progressive context scanner** (`scripts/scan_context.py`): Token-efficient
  context discovery with three progressive subcommands: `index` (list all
  documents, filterable by area/type), `outline` (section headings with word
  counts), and `extract` (raw section content). Reduces typical context lookup
  from ~8,500 tokens (4 Read calls) to ~700-1,000 tokens (2 Bash calls).
  ([#12](https://github.com/bcbeidel/wos/issues/12))
- **Discover skill** (`/wos:discover`): Routes agents through the progressive
  index → outline → extract pattern for finding and accessing context.

### Changed

- **AGENTS.md is now the primary config file.** The context manifest (area
  table between `<!-- wos:context:begin/end -->` markers) is written to
  AGENTS.md instead of CLAUDE.md. CLAUDE.md becomes a thin pointer with an
  `@AGENTS.md` reference so Claude Code loads it. Existing CLAUDE.md files
  with old-style markers are automatically migrated on the next discovery run.
  `check_manifest_sync` now validates AGENTS.md instead of CLAUDE.md.
  ([#23](https://github.com/bcbeidel/wos/issues/23))
- **Human-readable health output** is now the default. `scripts/check_health.py`
  outputs formatted text with issues sorted by severity, one line per issue in
  summary mode, or grouped by severity with suggestions in `--detailed` mode.
  JSON output preserved via `--json` flag. Basic ANSI color auto-detected on
  TTY, disabled with `--no-color`.
  ([#15](https://github.com/bcbeidel/wos/issues/15))
- Audit skill workflows simplified to show text output directly instead of
  instructing the LLM to parse and format JSON.

## [0.1.8] - 2026-02-19

### Added

- **Note document type** (`document_type: note`): A generic document type with
  minimal frontmatter requirements (`document_type` + `description` only). Notes
  can live anywhere in the repo without failing health checks, have no required
  sections, no directory constraints, and are excluded from the CLAUDE.md
  manifest. Useful for work products that don't fit the topic/overview/research/
  plan schema — decision records, reading notes, templates, personal docs, etc.
  ([#5](https://github.com/bcbeidel/wos/issues/5))

## [0.1.7] - 2026-02-18

### Improved

- **Report-issue skill: quality gates, framing guidance, and LLM invocability.**
  The `/wos:report-issue` skill now produces higher-quality issues with three
  changes: (1) the agent can invoke the skill proactively when it discovers WOS
  issues during normal work (`disable-model-invocation` removed), (2) templates
  include evaluation criteria, MRE sections, scope/non-goals, and before/after
  examples matching the quality standard of issue #12, (3) a framing rule in the
  drafting phase prevents consumer-specific language, and an advisory quality
  checklist is shown alongside the preview before submission.
  ([#14](https://github.com/bcbeidel/wos/issues/14))

## [0.1.6] - 2026-02-18

### Improved

- **Health check error messages now include expected section lists** for both
  `check_section_presence` and `check_section_ordering` validators. When a
  section is missing or misordered, the `suggestion` field lists all required
  sections in canonical order for that document type, eliminating the
  "whack-a-mole" pattern of fixing one section, re-running health, and
  discovering the next. ([#9](https://github.com/bcbeidel/wos/issues/9))

## [0.1.5] - 2026-02-18

### Added

- **Source URL reachability checking** (`wos/source_verification.py`): Lightweight
  HEAD-request reachability check for source URLs, wired into `/wos:health` behind
  `--tier2` flag. Cross-validator deduplicates URLs across documents and reports
  unreachable (404, DNS, timeout) as `warn` and access-restricted (403) as `info`.

## [0.1.4] - 2026-02-18

### Added

- **Token budget estimation** (`wos/token_budget.py`): Estimates aggregate token
  cost of context files using a `words × 1.3` heuristic, grouped by area. Always
  included in `/wos:health` output as a `token_budget` key with per-area breakdown,
  total estimate, and configurable warning threshold (default 40K tokens). Emits
  `severity: warn` issue when total context exceeds threshold.
  ([#7](https://github.com/bcbeidel/wos/issues/7))

### Fixed

- Pre-existing lint issues in `tests/test_source_verification.py` (unused import,
  line length, import sorting)

## [0.1.3] - 2026-02-18

### Added

- **Source URL verification** (`wos/source_verification.py`): Mechanical
  verification pass that checks cited source URLs resolve and page titles match
  cited titles. Catches hallucinated sources, dead links, and title mismatches
  before they propagate into context files. ([#6](https://github.com/bcbeidel/wos/issues/6))
  - `verify_sources()` for batch URL checking with structured `VerificationResult` output
  - HTTP status handling: 404/DNS/timeout → removed; 403/5xx/cross-domain redirect → flagged
  - Title comparison via normalized substring matching (lowercase, strip punctuation, collapse whitespace)
  - HTML `<title>` extraction with `<h1>` fallback using stdlib `html.parser`
  - CLI entry point: `python3 -m wos.source_verification` (JSON stdin/stdout, human summary on stderr)
- **Research skill workflow integration**: New Phase 3 (Verify Sources) inserted
  between source gathering and SIFT evaluation in `research-investigate.md`,
  with `source-verification.md` reference for agent instructions

### Fixed

- `titles_match()` no longer vacuously matches when either title normalizes to
  an empty string
- `verify_source()` now catches all `requests.RequestException` subclasses
  (e.g., `TooManyRedirects`, `SSLError`) instead of only `ConnectionError` and
  `Timeout`

### Changed

- Added `requests>=2.28` to project dependencies

## [0.1.2] - 2026-02-18

### Changed

- **Rename work-os → wos** across entire project for consistency with plugin
  prefix (`/wos:`). GitHub repo renamed `bcbeidel/work-os` → `bcbeidel/wos`.
- Context markers: `<!-- wos:context:begin -->` / `<!-- wos:context:end -->`
- Rules file: `.claude/rules/wos-context.md`
- Data directory: `.wos/` (was `.work-os/`)
- Package name in pyproject.toml: `wos`
- Marketplace and plugin config: name and repo updated

## [0.1.0] - 2026-02-18

First complete release of wos — a Claude Code plugin for building and
maintaining structured project context. All 10 v0.1-foundation phases
implemented with 229 tests passing.

### Added

#### Foundation (Phases 1.1–1.2)

- **Document type models** (`wos/document_types.py`): Pydantic v2 models for
  four document types (topic, overview, research, plan) with discriminated
  union `parse_document()`, dispatch tables for sections, size bounds, and
  directory patterns
- **Discovery layer** (`wos/discovery.py`): Auto-generates CLAUDE.md manifest
  with marker-delimited `## Context` section, `.claude/rules/work-os-context.md`
  rules file, and AGENTS.md mirroring — all derived from files on disk (note: rules file renamed to `.claude/rules/wos-context.md` in v0.1.2)

#### Core Skills (Phases 2.1–3.2)

- **Setup skill** (`/wos:setup`): Project scaffolding with `context/` directory
  structure, area creation with `_overview.md` files, discovery artifact
  generation
- **Health skill** (`/wos:health`): Type-dispatched Tier 1 validators (section
  presence/ordering, size bounds, directory placement, staleness, source
  diversity), Tier 2 LLM triggers, cross-validators (link graph, overview-topic
  sync, manifest drift, naming conventions), CLI entry point with JSON output
- **Curate skill** (`/wos:curate`): Document creation and update workflows for
  all four types, template rendering with `parse_document()` round-trip
  validation, manifest regeneration after context-type changes
- **Maintain skill** (`/wos:maintain`): Auto-fix engine with dispatch table
  (section reordering, missing sections, last_updated), lifecycle state machine
  for plan status transitions, manifest regeneration, cleanup for unparseable
  files

#### Standalone Skills (Phases 4.1–4.2)

- **Report-issue skill** (`/wos:report-issue`): GitHub issue submission workflow
  via `gh` CLI with context gathering, issue classification, draft preview,
  and explicit approval before submission
- **Consider skill** (`/wos:consider`): 16 mental model files (first-principles,
  inversion, pareto, 5-whys, SWOT, etc.) with uniform structure for structured
  reasoning

#### Capability Skills (Phase 5.1)

- **Research skill** (`/wos:research`): SIFT-based investigation framework with
  8 modes (deep dive, landscape, technical, feasibility, competitive, options,
  historical, open source), T1–T6 source hierarchy, and structured output as
  research documents

#### Extended Skills (Phase 6.1)

- **Observe skill** (`/wos:observe`): PostToolUse hook for auto-logging Read
  access to context files, utilization data layer (JSONL append-only log with
  record/aggregate/purge), recommendations engine with 6 categories
  (stale_high_use, never_referenced, low_utilization, hot_area, cold_area,
  expand_depth) gated by minimum data thresholds, dashboard/recommendations/
  trends workflows

#### Infrastructure

- Plugin manifest (`.claude-plugin/plugin.json`) with `/wos:` skill prefix
- GitHub Actions CI with pytest + ruff on push
- Design documents and research artifacts in `artifacts/research/v0.1-foundation/`
- Build roadmap with session protocol and dependency graph
- 18 design principles across four layers

[0.2.1]: https://github.com/bcbeidel/wos/releases/tag/v0.2.1
[0.2.0]: https://github.com/bcbeidel/wos/releases/tag/v0.2.0
[0.1.9]: https://github.com/bcbeidel/wos/releases/tag/v0.1.9
[0.1.8]: https://github.com/bcbeidel/wos/releases/tag/v0.1.8
[0.1.7]: https://github.com/bcbeidel/wos/releases/tag/v0.1.7
[0.1.6]: https://github.com/bcbeidel/wos/releases/tag/v0.1.6
[0.1.5]: https://github.com/bcbeidel/wos/releases/tag/v0.1.5
[0.1.4]: https://github.com/bcbeidel/wos/releases/tag/v0.1.4
[0.1.3]: https://github.com/bcbeidel/wos/releases/tag/v0.1.3
[0.1.2]: https://github.com/bcbeidel/wos/releases/tag/v0.1.2
[0.1.0]: https://github.com/bcbeidel/wos/releases/tag/v0.1.0
