# DDD Domain Model Enrichment

## Problem

The WOS domain model uses Pydantic but doesn't fully leverage DDD principles.
Domain logic is spread across helper modules (validators.py, formatting.py,
templates.py, token_budget.py) rather than living on the objects themselves.
This creates indirection, dict-based interfaces, and objects that are data
containers rather than rich domain models.

## Goals

1. Every domain object implements a standard DDD protocol
2. Helper modules are absorbed into the domain objects they serve
3. Test builders provide easy construction of valid test objects
4. CLAUDE.md documents the protocol so future work stays consistent

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

### Validation

- `validate_self(deep=False) -> list[ValidationIssue]` -- non-throwing consistency check
- `is_valid -> bool` -- shortcut property (`not self.validate_self()`)
- `deep=True` enables I/O checks (e.g., URL reachability)

### Collection (composite objects only)

- `__len__` -- count of primary contained items
- `__iter__` -- iterate over primary contained items
- `__contains__` -- membership test

### Token Estimation

- `get_estimated_tokens() -> int` -- estimated token cost

### Test Builders (tests/builders.py)

- `make_*(​**overrides) -> T` -- plain functions returning valid default objects

## Per-Object Protocol

### Value Objects (frozen=True)

| Object | `__str__` | json | markdown | validate_self | tokens |
|---|---|---|---|---|---|
| `CitedSource` | `[title](url)` | yes | `[t](u)` | url scheme, title; deep: reachability | yes |
| `ValidationIssue` | `[FAIL] file: msg` | yes | `- **FAIL** file: msg` | severity valid, file set | no |
| `DocumentSection` | `## Name (N words)` | yes | `## Name\n\ncontent` | content not empty | yes |
| `SectionSpec` | `Guidance @1` | yes | no | position > 0 | no |
| `SizeBounds` | `10-500 lines` | yes | no | min <= max | no |
| `VerificationResult` | `ok: url` | yes | no | http_status valid | no |
| `ReachabilityResult` | `reachable: url` | yes | no | url format valid | no |

### Documents (mutable -- not frozen)

| Object | validate_self absorbs | to_markdown absorbs |
|---|---|---|
| `BaseDocument` | validators.py shared checks | parse_document inverse |
| `TopicDocument` | topic-specific validators | templates.render_topic |
| `OverviewDocument` | overview-specific validators | templates.render_overview |
| `ResearchDocument` | research-specific validators | templates.render_research |
| `PlanDocument` | plan-specific validators | templates.render_plan |
| `NoteDocument` | title heading check | templates.render_note |

Documents also gain:
- `from_markdown(cls, path, content)` -- wraps parse_document, returns correct subclass
- `to_markdown()` -- renders full document with frontmatter (absorbs templates.py)
- `area_name -> Optional[str]` -- property extracting area from path (replaces 3 regex duplicates)
- `apply_fix(issue) -> Optional[BaseDocument]` -- absorbs auto_fix.py logic
- `__len__` -- number of sections
- `__iter__` -- iterate over sections
- `__contains__` -- check section name membership

### Aggregates

| Object | Construction | Representations | Collection |
|---|---|---|---|
| `ContextArea` | `from_directory(cls, root, name)` (exists), `from_documents(cls, docs)` (new) | `to_manifest_entry()` (exists), `to_json()` | `__len__` = topic count, `__iter__` = topics, `__contains__` = topic name |
| `HealthReport` | `from_project(cls, root, **opts)` (new factory) | `__str__` = summary line, `format_detailed()` absorbs formatting.py | `__len__` = issue count, `__iter__` = issues, `__contains__` = issue |

## Line Number Tracking

The parsing layer (`_split_markdown`) uses character offsets internally but
discards positional information. Adding line numbers enables LLMs to selectively
read specific sections of large documents and produces better error messages.

### Changes

**`DocumentSection`** gains:
- `line_start: Optional[int]` -- 1-indexed line where `## Heading` appears
- `line_end: Optional[int]` -- 1-indexed last line of section content

**`BaseDocument`** gains:
- `frontmatter_line_start: int` -- always 1 (first `---`)
- `frontmatter_line_end: int` -- line of closing `---`
- `title_line: Optional[int]` -- line of `# Title` heading

**`_split_markdown()`** updated to compute line numbers from character positions:
```python
line_number = content[:char_offset].count('\n') + 1
```

### Use Cases

- **LLM selective reading:** "Read lines 45-67 for the Pitfalls section"
- **Precise error messages:** "Issue on line 52" vs "in section Pitfalls"
- **Auto-fix targeting:** Fix functions can target exact line ranges
- **Token-aware partial loading:** Skip sections that exceed token budget

## Additional Absorptions

### `BaseDocument.area_name` property

Three separate places extract area name from `doc.path` via
`re.match(r"context/([^/]+)/", path)`:
- `token_budget._extract_area()`
- `cross_validators._build_context_areas()`
- `cross_validators.check_overview_topic_sync()`

Becomes: `BaseDocument.area_name -> Optional[str]` property.

### `ContextArea.from_documents(docs)` factory

`cross_validators._build_context_areas()` groups parsed documents into
ContextArea objects by regex. This is a second construction path that belongs
as a classmethod on ContextArea.

### `CitedSource.to_yaml_entry()`

`templates._render_sources_yaml()` serializes sources to YAML. This belongs
on the CitedSource object: `source.to_yaml_entry() -> str`.

### `BaseDocument.apply_fix(issue)` method

`auto_fix.py` takes raw markdown + issue, re-parses internally. Should take a
BaseDocument and return a new BaseDocument (or None if no fix applies).

### Duplicate `_display_name()` in scaffold.py

Same logic as `ContextArea.display_name` property. Scaffold should import and
use the ContextArea method instead.

## Modules Absorbed

| Module | Absorbed into | What remains |
|---|---|---|
| `validators.py` | Document subclass `validate_self()` methods | `validate_document()` becomes thin wrapper calling `doc.validate_self()` |
| `formatting.py` | `HealthReport.__str__` and `HealthReport.format_detailed()` | Deleted or re-exported for backward compat |
| `templates.py` | Document subclass `to_markdown()` methods | Helper functions `_render_sections()`, `_escape_yaml()` may stay as private utils |
| `token_budget.py` | `HealthReport.from_project()` or stays as utility | TBD -- may stay if budget logic is complex enough to warrant separation |
| `source_verification.py` | Result types become Pydantic models | Verification logic stays; only types change |

## Implementation Order (Bottom-Up)

### Phase 1: Value Objects
1. `CitedSource` -- add frozen, str, repr, validate_self(deep), from_json, to_json, to_markdown, from_markdown_link, to_yaml_entry; builder
2. `ValidationIssue` -- add frozen, str, repr, validate_self, from_json, to_json, to_markdown; builder
3. `DocumentSection` -- add frozen, str, repr, validate_self, from_json, to_json, to_markdown, line_start/line_end fields; builder
4. `SectionSpec` -- add frozen, str, repr, validate_self, from_json, to_json; builder
5. `SizeBounds` -- add frozen, str, repr, validate_self, from_json, to_json; builder

### Phase 2: Verification Result Types
6. `VerificationResult` -- migrate from dataclass to Pydantic, add protocol; builder
7. `ReachabilityResult` -- migrate from dataclass to Pydantic, add protocol; builder

### Phase 3: Line Number Tracking
8. Update `_split_markdown()` to compute and store line numbers
9. Add `frontmatter_line_end`, `title_line` to BaseDocument
10. Update DocumentSection to populate `line_start`/`line_end` during parsing

### Phase 4: Document Hierarchy
11. `BaseDocument` -- add from_markdown, to_markdown, validate_self, str, repr, collection, area_name property, apply_fix; builder
12. `TopicDocument` -- absorb topic validators + template; builder
13. `OverviewDocument` -- absorb overview validators + template; builder
14. `ResearchDocument` -- absorb research validators + template; builder
15. `PlanDocument` -- absorb plan validators + template; builder
16. `NoteDocument` -- absorb note template; builder

### Phase 5: Aggregates
17. `ContextArea` -- add str, repr, validate_self, to_json, collection, from_documents factory; builder
18. `HealthReport` -- add from_project factory, absorb formatting, collection; builder

### Phase 6: Cleanup & Deduplication
19. Thin out validators.py (backward compat wrappers only)
20. Delete or thin formatting.py
21. Thin out templates.py
22. Remove duplicate `_display_name()` from scaffold.py
23. Remove `_extract_area()` from token_budget.py (use doc.area_name)
24. Remove `_build_context_areas()` from cross_validators.py (use ContextArea.from_documents)
25. Update CLAUDE.md Domain Model Conventions section

## Convention Guard (CLAUDE.md Addition)

After implementation, CLAUDE.md gains a "Domain Model Conventions" section:

```
## Domain Model Conventions

All domain objects in `wos/models/` follow a standard DDD protocol:

- **Value objects** use `frozen=True` (immutable, hashable)
- **Construction:** `from_json(cls, dict)`, `from_markdown(cls, str)` where applicable
- **Representations:** `__str__`, `__repr__`, `to_json()`, `to_markdown()` where applicable
- **Validation:** `validate_self(deep=False) -> list[ValidationIssue]`, `is_valid` property
- **Collection:** composites implement `__len__`, `__iter__`, `__contains__`
- **Tokens:** `get_estimated_tokens()` where meaningful
- **Test builders:** `tests/builders.py` provides `make_*(**overrides)` for each type

New domain objects must implement this protocol. Do not add standalone
validator/formatter/template modules -- put behavior on the domain objects.
```

## Design Decisions

- **Bottom-up order:** Leaf types first (CitedSource, ValidationIssue), then
  composites (BaseDocument, HealthReport). Each PR is small and keeps tests green.
- **`validate_self(deep=False)`:** Fast local checks by default. `deep=True`
  enables I/O (HTTP reachability, file existence). Keeps validation fast in CI.
- **`frozen=True` on value objects only:** Documents need mutation for auto-fix.
  Value objects (CitedSource, ValidationIssue, etc.) are immutable.
- **Test builders are plain functions, not fixtures:** `tests/builders.py` with
  `make_*(**overrides)` functions. No pytest magic, importable from any test.
- **Backward compat wrappers:** validators.py and formatting.py get thin
  wrappers that delegate to domain methods. Removed in a follow-up if no
  external callers depend on them.

## References

- Cosmic Python (2.6k stars) -- value objects, entities, aggregates in Python
- Martin Fowler's Notification Pattern -- validate_self returning issues
- Luke Plant's test factory functions -- keyword-only builders with defaults
- Pydantic v2 frozen models -- ConfigDict(frozen=True) for value objects
