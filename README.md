# work-os

Personal work operating system — a Claude Code plugin for building and maintaining structured knowledge bases with AI-assisted research, structured reasoning, and quality validation.

## Why

Most AI-assisted work lacks rigor. Agents search and summarize without checking sources. Knowledge accumulates without structure. Quality degrades without validation. Work-os addresses this at three levels:

**Knowledge amplifier** — Structure what you know. Every piece of knowledge has provenance, validation dates, and clear paths to primary sources. Progressive disclosure means agents load what they need, not everything.

**Agent operating system** — Schema-first design where document type models are the single source of truth. Skills extend via dispatch tables. Discovery artifacts are derived, not hand-maintained. Free-text intake means no command memorization.

**Quality-first workflow** — SIFT framework for source evaluation. Mental models for structured reasoning. Three-tier validation (deterministic, LLM-assisted, human). If it can't be measured, it can't be maintained.

See [Design Principles](artifacts/research/2026-02-17-design-principles.md) for the full 18 principles grounded in agent context research, cognitive science, and software engineering practice.

## Architecture

```
                          User Intent
                              |
                    +---------+---------+
                    |   Claude Code     |
                    |   Plugin System   |
                    +---------+---------+
                              |
          +-------------------+-------------------+
          |                   |                   |
    Core Skills         Capability Skills    Extended Skills
   (build first)        (build second)       (build later)
          |                   |                   |
  +-------+-------+    +-----+-----+    +--------+--------+
  |setup  |curate |    |research   |    |import  |observe |
  |health |maintain|    |consider   |    |history |connect |
  |report-issue   |    |           |    |teach            |
  +---------+-----+    +-----+-----+    +-----------------+
            |                |
            v                v
  +------------------------------+
  |    Document Type Models      |
  |    (Pydantic v2 - source     |
  |     of truth)                |
  |  +------------------------+  |
  |  | Dispatch Tables:       |  |
  |  | SECTIONS, SIZE_BOUNDS, |  |
  |  | VALIDATORS_BY_TYPE,    |  |
  |  | TIER2_TRIGGERS,        |  |
  |  | DIRECTORY_PATTERNS,    |  |
  |  | TEMPLATES              |  |
  |  +------------------------+  |
  +------------------------------+
```

### Document Type System

Four document types organized on two axes:

```
                    Reference (consult)       Action (do/decide)
                   +---------------------+---------------------+
  Curated Context  |  topic   overview   |                     |
                   +---------------------+---------------------+
  Work Artifact    |  research           |  plan               |
                   +---------------------+---------------------+

  /context/                          /artifacts/
    {area}/                            research/
      overview.md   (overview)           {YYYY-MM-DD}-{slug}.md   (research)
      {topic}.md    (topic)            plans/
                                         {YYYY-MM-DD}-{slug}.md   (plan)
```

### Discovery Layer

```
  CLAUDE.md                          .claude/rules/
  (manifest)                         dewey-knowledge-base.md
  +---------------------------+      (rules file)
  | <!-- dewey:kb:begin -->   |      +---------------------------+
  | ## Knowledge Base         |      | Document types & rules    |
  |                           |      | When to create each type  |
  | ### chess                 |      | Frontmatter requirements  |
  | | Topic | Description |  |      | How to use related links  |
  | | Opening | Core pri...|  |      +---------------------------+
  | <!-- dewey:kb:end -->     |           |
  +---------------------------+           | auto-generated
            |                             | by scaffold
            | auto-generated              |
            | from /context/ files        |
            v                             v
  +-------------------------------------------+
  |        Files on disk (source of truth)     |
  +-------------------------------------------+
```

### Skill Dependencies

```
  consider --> research --> curate --> health --> maintain
                             |          |          |
                             |          |          +-- fix, lifecycle, regenerate
                             |          +-- validate, report
                             +-- create, update, promote

  setup ------------------------------------------------> (foundation)
  import ---------> curate ---------> health              (bulk path)
  observe <------------------------------------------------ (reads from all)
  history <------------------------------------------------ (tracks all changes)
  connect ---------> health, observe                       (external pipes)
  teach <-------------------------------------------------- (explains all)
```

## Skills

### Core (Tier 1)

| Skill | Purpose |
|-------|---------|
| `setup` | Initialize knowledge base, scaffold directories, add domain areas |
| `curate` | Create, update, ingest, propose, promote documents (all 4 types) |
| `health` | Type-dispatched validation: Tier 1 deterministic, Tier 2 LLM, Tier 3 human |
| `maintain` | Auto-fix, lifecycle transitions, manifest regeneration, cleanup |
| `report-issue` | Submit feedback and bug reports to the source repo via `gh` |

### Capability (Tier 2)

| Skill | Purpose |
|-------|---------|
| `research` | SIFT-based deep investigation with 8 modes (deep dive, landscape, technical, feasibility, competitive, options, historical, open source) |
| `consider` | 16 mental model commands for structured reasoning (first principles, inversion, Occam's razor, etc.) |

### Extended (Tier 3 — future)

| Skill | Purpose |
|-------|---------|
| `import` | Bulk ingest from existing docs, wikis, Notion, Confluence |
| `observe` | Utilization tracking, effectiveness analytics |
| `history` | Git-based document evolution tracking |
| `connect` | CI integration, doc site generation, project tracker sync |
| `teach` | Interactive onboarding and system guidance |

## Repository Structure

```
work-os/
  .claude-plugin/plugin.json     # Plugin manifest
  skills/                         # Claude Code skills
    setup/                        # Initialize and scaffold
    curate/                       # Content lifecycle
    health/                       # Quality validation (read-only)
    maintain/                     # Act on health signals (write)
    research/                     # SIFT-based investigation
    consider/                     # Mental model commands
    report-issue/                 # GitHub issue submission
  agents/                         # Custom agent definitions
  hooks/                          # Event-driven hook configurations
  scripts/                        # Shared Python scripts
    document_types.py             # Pydantic models (source of truth)
    discovery.py                  # Manifest/rules generation
    scaffold.py                   # Directory scaffolding
    templates.py                  # Document templates
    validators.py                 # Tier 1 per-file validators
    cross_validators.py           # Tier 1 cross-file validators
    tier2_triggers.py             # Tier 2 LLM trigger pre-screeners
    check_knowledge_base.py       # CLI health check entry point
    auto_fix.py                   # Automated issue correction
  artifacts/
    research/                     # Research documents
    plans/                        # Implementation plans
  tests/                          # Test suite
```

## Implementation Plans

Plans in `artifacts/plans/` (build order):

| Phase | Plan | Status |
|-------|------|--------|
| Foundation | [Document Type Models](artifacts/plans/2026-02-17-document-type-models.md) | draft |
| Foundation | [Discovery Layer](artifacts/plans/2026-02-17-discovery-layer.md) | draft |
| Core | [Setup Skill](artifacts/plans/2026-02-17-skill-setup.md) | draft |
| Core | [Curate Skill](artifacts/plans/2026-02-17-skill-curate.md) | draft |
| Core | [Health Skill](artifacts/plans/2026-02-17-skill-health.md) | draft |
| Core | [Maintain Skill](artifacts/plans/2026-02-17-skill-maintain.md) | draft |
| Core | [Report-Issue Skill](artifacts/plans/2026-02-17-skill-report-issue.md) | draft |
| Capability | [Research Skill](artifacts/plans/2026-02-17-skill-research.md) | draft |
| Capability | [Consider Skill](artifacts/plans/2026-02-17-skill-consider.md) | draft |
| Extended | [Observe Skill](artifacts/plans/2026-02-17-skill-observe.md) | draft |

## Design Documents

Design docs are in `artifacts/research/`:

- [Document Type Reference](artifacts/research/2026-02-16-document-type-reference.md) — concise rules (~170 lines)
- [Document Type Specification](artifacts/research/2026-02-16-document-type-specification.md) — normative spec with rationale
- [Document Type Data Models](artifacts/research/2026-02-16-document-type-data-models.md) — Pydantic models and validators
- [Skills Architecture Design](artifacts/research/2026-02-17-skills-architecture-design.md) — skills and discovery layer
- [Deep Dive Research](artifacts/research/2026-02-17-document-type-system-deep-dive.md) — evidence base

## Usage

```bash
claude --plugin-dir /path/to/work-os
```

Or add to Claude Code settings for automatic loading.

## Dependencies

- Python 3.9+
- `pydantic>=2.0`
- `gh` CLI (for report-issue skill)
