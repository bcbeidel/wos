# Changelog

All notable changes to work-os will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-18

First complete release of work-os — a Claude Code plugin for building and
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
  rules file, and AGENTS.md mirroring — all derived from files on disk

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

[0.1.0]: https://github.com/bcbeidel/work-os/releases/tag/v0.1.0
