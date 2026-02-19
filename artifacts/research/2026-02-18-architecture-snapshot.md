---
document_type: research
description: "Canonical design document capturing WOS intent, architecture, principles, and current state as of v0.1.6"
last_updated: 2026-02-18
sources:
  - url: "https://diataxis.fr/"
    title: "Diataxis Documentation Framework"
  - url: "https://research.trychroma.com/context-rot"
    title: "Context Rot — Chroma Research"
  - url: "https://zettelkasten.de"
    title: "Zettelkasten Method"
  - url: "https://fortelabs.com/blog/para/"
    title: "PARA Method — Tiago Forte"
  - url: "https://agentskills.io"
    title: "Agent Skills Specification"
---

# WOS Architecture Snapshot (v0.1.6)

## Question

What is WOS — its intent, architecture, design principles, and current state?

This document is the canonical design reference for WOS. It consolidates the
research, specifications, and plans from the v0.1-foundation build into a
single self-contained record. If you read one document about WOS, read this
one.

## Findings

### Intent and Philosophy

WOS is a Claude Code plugin for building and maintaining structured project
context. It provides skills, scripts, and agents that help users create,
validate, and maintain knowledge bases in their own repositories.

WOS is a **tool**, not a project context itself. When working in the WOS repo,
you are building the tool. When WOS is installed as a plugin in another repo,
it operates on that repo's `/context/` directory.

The core value proposition: structured context makes agents more effective.
Instead of loading entire codebases into context, WOS helps users curate
domain-specific knowledge — actionable guidance, investigation snapshots, work
plans — that agents can discover and consume efficiently.

### Design Principles

WOS is built on 18 design principles across four layers.

#### Layer 1: Knowledge Amplifier

**1. Source Primacy** — The knowledge base is a curated guide, not a
replacement for primary sources. Every entry points to one. When an agent or
human needs to go deeper, the path is always clear.

**2. Dual Audience** — Every entry serves the agent (structured,
token-efficient context) and the human (readable, navigable content). When
these conflict, favor human readability — agents are more adaptable readers.

**3. Domain-Shaped Organization** — Organized around the domain's natural
structure, not file types or technical categories. The taxonomy should feel
intuitive to a practitioner.

**4. Right-Sized Scope** — Contains what's needed to be effective, and no
more. The curation act is as much about what you exclude as what you include.

**5. Progressive Disclosure** — Layered access so agents can discover what's
available without loading everything. Descriptions before full content.
Overviews before topics. Context before artifacts.

#### Layer 2: Agent Operating System

**6. Schema-First Design** — Document type models are the single source of
truth. Templates, validators, sections, size bounds, and directory rules all
derive from the models. Adding a new document type means adding to dispatch
tables — no routing changes, no scattered conditionals.

**7. Separation of Observation and Action** — Health observes (read-only,
CI-friendly). Maintain acts (write, requires approval). This separation
enables different permission models and prevents accidental modification.

**8. Convention Over Configuration** — Adding a new mental model is adding a
file. Adding a new document type is adding to dispatch tables. The system
should be extended by following patterns, not by writing integration code.

**9. Derived Artifacts, Not Source-of-Truth Artifacts** — The CLAUDE.md
manifest is a cache regenerated from disk. The rules file is auto-generated
from the schema. Discovery artifacts are always derivable, never the canonical
source.

**10. Free-Text Intake** — Users describe intent; the system classifies and
routes. No command memorization. The cost of misclassification is a redirect,
not a failure.

#### Layer 3: Quality-First Workflow

**11. SIFT at the Source** — Every piece of research passes through Stop,
Investigate, Find better, Trace claims. Sources are authority-checked before
inclusion. Claims are traced to primary sources, not secondary summaries.

**12. Structured Reasoning Before Action** — Mental models (first principles,
inversion, Occam's razor) are available as invocable tools, not afterthoughts.
Thinking clearly is a skill the system supports, not an assumption it makes.

**13. Three-Tier Validation** — Deterministic checks catch structural issues
(Python, fast, CI-friendly). LLM-assisted assessment catches quality issues
(Claude evaluates flagged items). Human judgment catches relevance and scope
issues. Each tier has a clear boundary.

**14. Empirical Feedback** — Observable signals about knowledge base health:
coverage gaps, stale entries, unused content, source drift. Proxy metrics
inform curation decisions. If it can't be measured, it can't be maintained.

**15. Provenance and Traceability** — Every piece of knowledge carries
metadata about where it came from, when it was last validated, and why it's in
the knowledge base. Research documents are the provenance trail for topics
they inform.

#### Layer 4: Cognitive Science

**16. Explain the Why** — Causal explanations produce better comprehension and
retention than stating facts alone (Dunlosky et al., 2013 — elaborative
interrogation). Every topic explains not just what to do, but why it works.

**17. Concrete Before Abstract** — Lead with examples and worked scenarios,
then build toward the abstraction (Paivio, 1986 — dual coding theory). The In
Practice section comes before the theory.

**18. Multiple Representations** — Important concepts exist at multiple levels
of depth (Kalyuga et al., 2003 — expertise reversal effect). Material that
helps novices can hinder experts — label each level clearly so readers
self-select.

### Architecture

#### Schema-First Design

Everything derives from Pydantic v2 document type models in
`wos/document_types.py`. The models define four document types and dispatch
tables that control every aspect of the system:

- `SECTIONS` — Required sections and canonical ordering per type
- `SIZE_BOUNDS` — Min/max line counts per type
- `DIRECTORY_PATTERNS` — Path regex per type
- `VALIDATORS_BY_TYPE` — Validator functions per type
- `OPTIONAL_SECTIONS` — Optional sections with placement rules

The `parse_document()` function is the single entry point for all document
parsing. It uses a discriminated union on the `document_type` frontmatter
field to route to the correct Pydantic model.

#### Extension Protocol

Adding a new document type requires exactly these steps:

1. Add a Pydantic frontmatter model (e.g., `InitiativeFrontmatter`)
2. Add the model to the `Frontmatter` discriminated union
3. Add entries to dispatch tables: `SECTIONS`, `SIZE_BOUNDS`,
   `DIRECTORY_PATTERNS`, `VALIDATORS_BY_TYPE`
4. Add a template function to `templates.py`
5. Done — all skills automatically pick up the new type

No skill routing changes. No discovery layer changes. No CLI changes.

#### Package Structure

The `wos/` package contains 14 modules organized into three groups:

**Core (6 modules):**
- `document_types.py` — Pydantic models, dispatch tables, `parse_document()`
- `validators.py` — Per-file validators dispatched by `VALIDATORS_BY_TYPE`
- `cross_validators.py` — Multi-file validators (link graph, manifest sync,
  naming conventions, source URL reachability)
- `templates.py` — Template functions for generating new documents
- `discovery.py` — Scans `/context/`, generates CLAUDE.md manifest, rules
  file, and AGENTS.md
- `scaffold.py` — Creates directory structures and overview templates

**Validation Extended (2 modules):**
- `tier2_triggers.py` — LLM-assisted quality assessment triggers
- `auto_fix.py` — Safe automated corrections (section reordering, missing
  sections, status transitions)

**Analytics and Utilities (5 modules):**
- `source_verification.py` — URL reachability and title verification
- `token_budget.py` — Token cost estimation with per-area breakdown
- `utilization.py` — Document access logging (JSONL append-only)
- `recommendations.py` — Data-driven curation suggestions
- `hook_log_access.py` — PostToolUse hook for auto-logging Read operations

CLI entry points live in `scripts/` as thin wrappers:
- `check_health.py` — Runs validators, outputs JSON
- `run_discovery.py` — Regenerates manifest and rules
- `run_scaffold.py` — Creates project/area scaffolding
- `run_auto_fix.py` — Applies safe automated corrections

### Document Type System

#### Four Document Types

| Type | Location | Purpose | Audience |
|------|----------|---------|----------|
| `topic` | `/context/{area}/{topic}.md` | Actionable guidance with citations | Agent + human |
| `overview` | `/context/{area}/_overview.md` | Area orientation and topic index | Agent + human |
| `research` | `/artifacts/research/{date}-{slug}.md` | Investigation snapshot | Internal |
| `plan` | `/artifacts/plans/{date}-{slug}.md` | Actionable work plan | Internal |

Context types (topic, overview) are **agent-facing** — they appear in the
CLAUDE.md manifest under `## Context`. Artifact types (research, plan) are
**internal work products**, reachable via `related` links.

#### Frontmatter Fields

| Field | Topic | Overview | Research | Plan |
|-------|:-----:|:--------:|:--------:|:----:|
| `document_type` | Required | Required | Required | Required |
| `description` | Required | Required | Required | Required |
| `last_updated` | Required | Required | Required | Required |
| `sources` | Required | — | Required | — |
| `last_validated` | Required | Required | — | — |
| `status` | — | — | Optional | Required |
| `tags` | Optional | Optional | Optional | Optional |
| `related` | Optional | Optional | Optional | Optional |

`description` must be 10+ characters. `sources` requires at least one entry
with `url` and `title`. `status` uses the enum: draft, active, complete,
abandoned. `tags` must be lowercase-hyphenated. `related` entries are
root-relative file paths or URLs.

#### Required Sections (in canonical order)

**Topic:** Guidance → Context → In Practice → Pitfalls → Go Deeper
(optional: Quick Reference between Pitfalls and Go Deeper)

**Overview:** What This Covers (min 30 words) → Topics → Key Sources

**Research:** Question → Findings → Implications → Sources

**Plan:** Objective → Context → Steps → Verification

Section ordering is grounded in cognitive science: Guidance first (primacy
effect — Murdock, 1962), In Practice early (engagement resistance), Go Deeper
last (recency effect — Glanzer & Cunitz, 1966).

#### Size Constraints

| Type | Min Lines | Max Lines |
|------|-----------|-----------|
| Topic | 10 | 500 |
| Overview | 5 | 150 |
| Research | 20 | — |
| Plan | 10 | — |

Line counts are deterministic and enforced. The token budget module provides
an additional aggregate estimate (words × 1.3 heuristic) with a configurable
warning threshold (default 40K tokens).

#### Document Lifecycle

```
Research → informs → Plan → produces → Topics + Overviews
                                    → may trigger → more Research
```

- Research documents are **point-in-time snapshots** — they don't update after
  completion
- Plans are **living documents** with status transitions (draft → active →
  complete/abandoned)
- Topics and overviews are **maintained long-term** via `last_validated`
- Plans reference research in their Context section (provenance chain)
- Topics may reference their originating plan via `related`

### Skill Inventory

WOS provides 8 skills, all prefixed `/wos:`. Each skill has `SKILL.md`
(routing metadata), `workflows/` (step-by-step instructions), and optionally
`references/` (supporting material).

#### Core Skills

**`/wos:setup`** — Project scaffolding. Creates `/context/` directory
structure, area directories with `_overview.md` files, and runs discovery to
generate manifest. Runs once or rarely. Side effects: creates files.

**`/wos:health`** — Read-only validation and reporting. Three-tier system:
Tier 1 (deterministic checks), Tier 2 (LLM triggers, behind `--tier2`), Tier
3 (human Q&A in conversation). Five workflows: check, audit, review, coverage,
freshness. CI-friendly JSON output. No side effects.

**`/wos:curate`** — Document creation and update. Free-text intake classifies
intent into four paths (research, plan, topic, overview). Validates via
`parse_document()` before writing. Regenerates manifest after context-type
changes. Side effects: creates/modifies files.

**`/wos:maintain`** — Write operations acting on health signals. Auto-fix
engine (section reordering, missing sections), lifecycle status transitions
for plans, manifest regeneration, cleanup of unparseable files. All changes
require user confirmation. Side effects: modifies files.

#### Standalone Skills

**`/wos:report-issue`** — GitHub issue submission via `gh` CLI. Gathers
context, classifies (bug/feature/feedback), previews draft, submits only with
explicit approval. Target: `bcbeidel/wos` repo.

**`/wos:consider`** — 16 mental models for structured reasoning:
first-principles, inversion, occam's-razor, second-order, eisenhower-matrix,
opportunity-cost, via-negativa, pareto, 5-whys, SWOT, 10-10-10, one-thing,
circle-of-competence, map-vs-territory, reversibility, hanlons-razor. Each
file is under 60 lines with uniform structure.

#### Advanced Skills

**`/wos:research`** — SIFT-based investigation framework with 8 modes:
deep-dive, landscape, technical, feasibility, competitive, options,
historical, open-source. Structured source evaluation with T1–T6 authority
hierarchy. Outputs research-type documents.

**`/wos:observe`** — Usage analytics and curation recommendations.
PostToolUse hook auto-logs Read operations to `.wos/utilization.jsonl`. Six
recommendation categories: stale_high_use, never_referenced,
low_utilization, hot_area, cold_area, expand_depth. Gated by minimum data
thresholds (10+ reads, 14+ days).

### Validation Model

#### Tier 1: Deterministic (14 validators + 5 cross-validators)

Per-file validators (all types):
- `check_section_presence` — Required sections exist
- `check_section_ordering` — Sections in canonical order
- `check_size_bounds` — Line count within bounds
- `check_directory_placement` — File path matches pattern
- `check_title_heading` — H1 title exists
- `check_heading_hierarchy` — No heading level skips
- `check_placeholder_comments` — No TODO/FIXME markers
- `check_date_fields` — Date consistency

Type-specific validators:
- `check_last_validated` — Staleness (30d info, 60d warn, 90d stale) [topic, overview]
- `check_source_diversity` — Multiple domains [topic, research]
- `check_go_deeper_links` — Links present [topic]
- `check_what_this_covers_length` — Min 30 words [overview]
- `check_question_nonempty` — Non-empty question [research]
- `check_date_prefix_matches` — Filename date matches frontmatter [research, plan]

Cross-file validators:
- `check_link_graph` — Related file paths resolve (broken → fail)
- `check_overview_topic_sync` — Overview Topics table matches disk (mismatch → fail)
- `check_manifest_sync` — CLAUDE.md manifest matches disk (drift → warn)
- `check_naming_conventions` — Lowercase-hyphenated names
- `check_source_url_reachability` — HTTP HEAD checks (behind `--tier2`)

#### Tier 2: LLM-Assisted (9 triggers)

Triggers produce structured context for Claude to evaluate. They flag
candidates, not failures:
- `trigger_description_quality` — Short descriptions [all types]
- `trigger_in_practice_concreteness` — Missing code/bullets [topic]
- `trigger_pitfalls_completeness` — Sparse pitfalls [topic]
- `trigger_overview_coverage_quality` — Vague coverage [overview]
- `trigger_question_clarity` — Missing question mark [research]
- `trigger_finding_groundedness` — Missing citations [research]
- `trigger_step_specificity` — Low word-to-step ratio [plan]
- `trigger_verification_completeness` — Sparse verification [plan]

#### Tier 3: Human Judgment

Structured Q&A in conversation (not a queue file). Used for relevance, scope,
and correctness decisions that require domain expertise.

#### Auto-Fix Engine

Safe automated corrections dispatched by validator name:
- `fix_section_ordering` — Reorders sections to canonical order
- `fix_missing_sections` — Adds missing sections with TODO placeholders
- `transition_status` — Plan lifecycle transitions with valid state machine

All fixes validate the result via `parse_document()` before returning.

### Severity Conventions

| Condition | Severity |
|-----------|----------|
| Broken `related` file path | fail |
| Overview-topic sync mismatch | fail |
| Missing/misordered sections | warn |
| Manifest drift | warn |
| Unreachable source URL (404) | warn |
| Access-restricted URL (403) | info |
| Staleness: 30d | info |
| Staleness: 60d | warn |
| Staleness: 90d | warn |
| Placeholder comments | info |

### Key Conventions

- Python 3.9 — `from __future__ import annotations` for type hints,
  `Optional[X]` for runtime expressions
- Validators return `list[dict]` with keys: file, issue, severity, validator,
  section, suggestion (same shape for per-file and cross-validators)
- All document operations validate via `parse_document()` before writing
- CLI scripts default to CWD as root; accept `--root` for override
- Skills use free-text intake — users describe intent, Claude routes
- Pydantic `ValidationError` + stdlib exceptions only (no custom exception
  hierarchy)
- Tests use inline markdown strings (no fixture files)
- Plugin prefix: `/wos:` (controlled by `name` field in
  `.claude-plugin/plugin.json`)

### Build History

WOS v0.1 was built across 10 phases:

| Phase | Deliverable |
|-------|-------------|
| 1.1 | Document type models (`wos/document_types.py`) — Pydantic v2 models, discriminated union, dispatch tables |
| 1.2 | Discovery layer (`wos/discovery.py`) — CLAUDE.md manifest, rules file, AGENTS.md generation |
| 2.1 | Setup skill — Project/area scaffolding with `_overview.md` templates |
| 2.2 | Health skill — 14 per-file validators, 5 cross-validators, 9 Tier 2 triggers, JSON CLI |
| 3.1 | Curate skill — Document creation/update with template rendering and validation |
| 3.2 | Maintain skill — Auto-fix engine, plan lifecycle state machine, manifest regeneration |
| 4.1 | Report-issue skill — GitHub issue submission via `gh` CLI |
| 4.2 | Consider skill — 16 mental model files for structured reasoning |
| 5.1 | Research skill — SIFT framework with 8 investigation modes |
| 6.1 | Observe skill — Utilization tracking, recommendations engine, PostToolUse hook |

Post-v0.1 releases added source verification (v0.1.3), token budget estimation
(v0.1.4), source URL reachability (v0.1.5), and improved health check error
messages (v0.1.6). The project rename from `work-os` to `wos` happened in
v0.1.2.

## Implications

### What This Architecture Enables

**Extensibility** — Adding a new document type is a ~10-line change to
dispatch tables. No skill routing, discovery, or CLI changes needed. The
dispatch table pattern means the system scales without accumulating
conditional logic.

**CI Integration** — Health checks are deterministic, JSON-formatted, and
exit with code 1 on failures. They can run in GitHub Actions with zero
configuration beyond `python3 scripts/check_health.py`.

**Agent-Friendly Output** — Health check suggestions include the full expected
section list, so agents can fix all issues in one pass without iterative
discovery. Token budget estimates help agents understand context cost.

**Observation Without Mutation** — The health/maintain separation means
read-only checks can run freely (CI, agent invocation) while writes always
require explicit approval. This matches Claude Code's permission model.

### Current State

As of v0.1.6: 14 Python modules, 8 skills, 305 tests passing, 16 mental
models. The v0.1-foundation roadmap is complete.

### Open Issues

- **#5** — Template scaffolding and validation support
- **#12** — Progressive context scanner for token-efficient discovery
- **#14** — Improve report-issue skill with quality gates and eval requirements

## Sources

### Documentation Standards
- Diataxis Framework — https://diataxis.fr/
- OASIS DITA 1.3 Specification
- Mark Baker, *Every Page is Page One* (XML Press, 2013)
- Robert E. Horn, "Structured Writing as a Paradigm" (1998)

### Agent Context Engineering
- Anthropic, "Effective Context Engineering for AI Agents" (2025)
- Agent Skills Specification — https://agentskills.io
- Chroma Research, "Context Rot" (2025) — https://research.trychroma.com/context-rot
- Liu et al., "Lost in the Middle" (TACL, 2024)

### Personal Knowledge Management
- Zettelkasten Method — https://zettelkasten.de
- Tiago Forte, PARA Method — https://fortelabs.com/blog/para/
- Andy Matuschak, Evergreen Notes — https://notes.andymatuschak.org
- Nick Milo, LYT / Maps of Content framework
- Johnny Decimal system — https://johnnydecimal.com

### ADRs, RFCs, and Design Docs
- Michael Nygard, "Documenting Architecture Decisions" (Cognitect, 2011)
- MADR template — https://adr.github.io/madr
- Rust RFC process — https://rust-lang.github.io/rfcs
- Python PEP 1 and PEP 12 — https://peps.python.org
- Malte Ubl, "Design Docs at Google" — https://industrialempathy.com
- Gergely Orosz, "Engineering Planning with RFCs" (Pragmatic Engineer)

### Cognitive Science
- Ebbinghaus serial position effect; Murdock (1962); Glanzer & Cunitz (1966)
- Sweller, "Cognitive Load Theory" (1988)
- Paivio, "Mental Representations: A Dual Coding Approach" (1986)
- Pirolli & Card, "Information Foraging" (Psychological Review, 1999)
- Kalyuga et al., "Expertise Reversal Effect" (Educational Psychologist, 2003)
- Bjork, "Memory and Metamemory Considerations" (1994)
- Dunlosky et al., "Improving Students' Learning" (Psych. Sci. Public Interest, 2013)
