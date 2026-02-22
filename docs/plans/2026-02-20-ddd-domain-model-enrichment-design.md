# DDD Domain Model Enrichment — Design

## Problem

The WOS domain model uses Pydantic but doesn't fully leverage DDD principles.
Domain logic is spread across helper modules (validators.py, auto_fix.py,
tier2_triggers.py, token_budget.py, discovery.py, scaffold.py) rather than
living on the objects themselves. This creates indirection, dict-based
interfaces, and objects that are data containers rather than rich domain models.

The project structure itself (areas, AGENTS.md, CLAUDE.md, rules file) lacks
first-class domain representation.

## Goals

1. Every domain object implements a standard DDD protocol
2. Helper modules are absorbed into the domain objects they serve
3. New domain objects model the project structure (ProjectContext, AgentsMd, etc.)
4. Three-tier validation: structural, content quality (LLM), reachability
5. Auto-fix as explicit user-initiated method, not constructor normalization
6. Object graph supports future CRUD CLI strategy for agent interaction
7. Test builders provide easy construction of valid test objects

## Future Direction: CRUD CLI

Long-term, skills will mirror CRUD operations on documents:
- **Create:** `from_template()`, `from_markdown()`
- **Read:** `to_json()`, `to_markdown()`, property access to frontmatter/sections
- **Update:** `auto_fix()`, section-level mutations
- **Delete:** `ProjectContext` collection management

Python CLI entry points will wrap these to minimize agent token consumption.
The domain model designed here supports this strategy without changes.

## DDD Protocol

Every domain object implements these capabilities:

### Construction

- `__init__(**fields)` -- Pydantic default
- `from_json(cls, data: dict) -> Self` -- construct from JSON-compatible dict
- `from_markdown(cls, text: str) -> Self` -- construct from markdown (where applicable)

### Equality & Identity

- `__eq__` -- value-based equality (Pydantic default)
- `__hash__` -- enabled via `frozen=True` on value objects

### Representations

- `__str__` -- human-readable display (CLI output, logs)
- `__repr__` -- debug representation (Pydantic default, customized where useful)
- `to_json() -> dict` -- JSON-serializable dict
- `to_markdown() -> str` -- markdown rendering (where applicable)

### Validation (Three Tiers)

| Tier | Method | Resolver | Example |
|------|--------|----------|---------|
| Structural | `validate_self()` | Machine / user | Missing section, bad ordering, size bounds |
| Content quality | `validate_content()` | LLM | Vague description, weak examples, unclear question |
| Reachability | `validate_self(deep=True)` | User | Broken URL, missing linked file |

- `validate_self(deep=False) -> list[ValidationIssue]` -- non-throwing consistency check
- `validate_content() -> list[ValidationIssue]` -- LLM-resolvable quality checks
- `is_valid -> bool` -- shortcut property (`not self.validate_self()`)
- `deep=True` enables I/O checks (e.g., URL reachability)
- `auto_fix() -> Self` -- fix machine-resolvable issues, user-initiated (never on construction)

`ValidationIssue` gains `requires_llm: bool` to distinguish structural vs content issues.

### Collection (composite objects only)

- `__len__` -- count of primary contained items
- `__iter__` -- iterate over primary contained items
- `__contains__` -- membership test

### Token Estimation

- `get_estimated_tokens() -> int` -- estimated token cost

### Test Builders (tests/builders.py)

- `make_*(**overrides) -> T` -- plain functions returning valid default objects

## Complete Object Graph

### ProjectContext (aggregate root, NEW)

```
ProjectContext
├── root: str
├── areas: list[ContextArea]
├── agents_md: AgentsMd
├── claude_md: ClaudeMd
├── rules_file: RulesFile
│
├── scaffold(areas: list[str])        # from scaffold.py
├── add_area(name: str)               # factory → ContextArea
├── discover()                        # scan → render → update files
├── validate_self(deep=False)         # cross-area checks (from cross_validators.py)
├── auto_fix()
├── is_valid
├── __len__, __iter__, __contains__   # over areas
```

### ContextArea (entity, ENRICH)

```
ContextArea
├── ... existing fields ...
├── validate_self(deep=False)         # absorbs cross_validators
├── auto_fix()
├── is_valid
├── get_estimated_tokens()            # from token_budget.py
```

### BaseDocument + Subclasses (entity, ENRICH)

```
BaseDocument
├── ... existing DDD protocol ...
├── validate_self(deep=False)         # structural (existing)
├── validate_content()                # LLM-resolvable quality (absorbs tier2_triggers)
├── auto_fix()                        # absorbs auto_fix.py
├── from_template()                   # absorbs templates.py (already started)
│
├── TopicDocument    → + validate_content() inlines concreteness, pitfalls checks
├── OverviewDocument → + validate_content() inlines coverage quality check
├── ResearchDocument → + validate_content() inlines question clarity, groundedness
├── PlanDocument     → + validate_content() inlines step specificity, verification
├── NoteDocument     → minimal (title check only)
```

### New Domain Objects

```
AgentsMd (entity, NEW)
├── path, content
├── update_manifest(areas)            # render between markers
├── validate_self(), is_valid
├── from_markdown(), to_markdown()

ClaudeMd (entity, NEW)
├── path, content
├── ensure_agents_ref()               # add @AGENTS.md, strip old markers
├── validate_self(), is_valid
├── from_markdown(), to_markdown()

RulesFile (value object, NEW)
├── content
├── render()                          # generate behavioral guide
├── validate_self(), is_valid, to_markdown()

CommunicationPreferences (value object, NEW)
├── dimensions: dict
├── render_section()                  # from preferences.py
├── validate_self(), is_valid
```

### Value Objects (frozen=True, already enriched)

| Object | `__str__` | json | markdown | validate_self | tokens |
|---|---|---|---|---|---|
| `CitedSource` | `[title](url)` | yes | `[t](u)` | url scheme, title; deep: reachability | yes |
| `ValidationIssue` | `[FAIL] file: msg` | yes | `- **FAIL** file: msg` | severity valid, file set; `requires_llm` field | no |
| `DocumentSection` | `## Name (N words)` | yes | `## Name\n\ncontent` | content not empty | yes |
| `SectionSpec` | `Guidance @1` | yes | no | position > 0 | no |
| `SizeBounds` | `10-500 lines` | yes | no | min <= max | no |
| `VerificationResult` | `ok: url` | yes | no | http_status valid | no |
| `ReachabilityResult` | `reachable: url` | yes | no | url format valid | no |

## Modules Absorbed

| Module | Absorbed into | What remains |
|---|---|---|
| `auto_fix.py` | `auto_fix()` on BaseDocument + subclasses | Deleted |
| `tier2_triggers.py` | `validate_content()` on each subclass | Deleted |
| `token_budget.py` | `get_estimated_tokens()` on ContextArea | Deleted |
| `templates.py` | `from_template()` on each subclass | Private utils may stay |
| `cross_validators.py` | `validate_self()` on ContextArea + ProjectContext | Deleted |
| `discovery.py` | `ProjectContext.discover()` | Thin CLI adapter |
| `scaffold.py` | `ProjectContext.scaffold()` / `.add_area()` | Thin CLI adapter |

## Modules That Stay

| Module | Reason |
|---|---|
| `formatting.py` | CLI presentation layer (not domain logic) |
| `validators.py` | Validator function library (called by `validate_self()`) |

## Line Number Tracking (already implemented)

`DocumentSection` has `line_start`/`line_end` fields populated during parsing.
`BaseDocument` has `frontmatter_line_end` and `title_line` properties.

## Implementation Sequencing

Bottom-up: leaf objects first, composites next, aggregates last.

### Phase A: Absorb into existing objects

1. `ValidationIssue` — add `requires_llm: bool` field
2. `BaseDocument.auto_fix()` — absorb shared fixes from `auto_fix.py`
3. Each subclass `auto_fix()` — absorb type-specific fixes
4. Each subclass `validate_content()` — inline tier2 trigger logic, return `ValidationIssue(requires_llm=True)`
5. `ContextArea.validate_self()` — absorb relevant cross-validators
6. `ContextArea.get_estimated_tokens()` — absorb token_budget logic

### Phase B: New domain objects

7. `RulesFile` — value object, simplest new object
8. `AgentsMd` — entity, owns manifest + marker logic
9. `ClaudeMd` — entity, owns @AGENTS.md reference + migration
10. `CommunicationPreferences` — value object from preferences.py

### Phase C: ProjectContext aggregate

11. `ProjectContext` — aggregate root, owns areas + file objects
12. `ProjectContext.scaffold()` — absorb scaffold.py
13. `ProjectContext.discover()` — absorb discovery.py orchestration
14. `ProjectContext.validate_self()` — absorb remaining cross-validators

### Phase D: Thin out modules

15. `discovery.py` → thin CLI adapter calling `ProjectContext.discover()`
16. `scaffold.py` → thin CLI adapter calling `ProjectContext.scaffold()`
17. Delete `auto_fix.py`, `tier2_triggers.py`, `token_budget.py`

Each phase has its own branch. Tests mirror source structure in `tests/models/`.

## Design Decisions

- **Bottom-up order:** Leaf types first, then composites, then aggregates.
  Each phase is small and keeps tests green.
- **Three-tier validation:** `validate_self()` for structural, `validate_content()`
  for LLM-resolvable, `deep=True` for I/O. Clear resolution paths.
- **`auto_fix()` is user-initiated:** Parse faithfully, validate later. Auto-fix
  is an explicit action, not constructor normalization.
- **No backward compatibility aliases:** Rename directly (e.g., `validate_structure`
  → `validate_self`). No shims.
- **`frozen=True` on value objects only:** Documents need mutation for auto-fix.
  Value objects (CitedSource, ValidationIssue, etc.) are immutable.
- **Test builders are plain functions:** `tests/builders.py` with
  `make_*(**overrides)`. No pytest magic, importable from any test.
- **`validators.py` stays as function library:** Subclasses import and call
  individual validators. No dispatch tables needed.
- **`formatting.py` stays separate:** CLI presentation is not domain logic.
- **`ProjectContext` as aggregate root:** Ties together areas, AGENTS.md,
  CLAUDE.md, rules file. Absorbs scaffold + discovery orchestration.

## References

- Cosmic Python (2.6k stars) -- value objects, entities, aggregates in Python
- Martin Fowler's Notification Pattern -- validate_self returning issues
- Luke Plant's test factory functions -- keyword-only builders with defaults
- Pydantic v2 frozen models -- ConfigDict(frozen=True) for value objects
