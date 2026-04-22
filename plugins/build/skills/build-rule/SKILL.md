---
name: build-rule
description: Create a Claude Code rule under `.claude/rules/` — a markdown instruction file with optional `paths:` frontmatter for path-scoping. Use when the user wants to "create a rule", "build a rule", "add a rule", "capture this convention", or "enforce this pattern".
argument-hint: A topic name or description of the convention to capture
user-invocable: true
references:
  - references/rule-format-guide.md
needs:
  - primitive-routing
---

# /build:build-rule

Create a Claude Code rule. Rules are markdown files in `.claude/rules/`
that Claude reads automatically — globally at session start (no frontmatter)
or on demand when a matching file is opened (with `paths:` frontmatter).
See [Anthropic's `.claude/rules/` reference](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/).

## Workflow

### 0. Verify Primitive

Before proceeding, confirm a rule is the right mechanism. Full decision matrix: [primitive-routing.md](../../_shared/references/primitive-routing.md).

A rule is right when:
- The instruction should always (or path-conditionally) shape Claude's
  behavior in a project — not fire as a one-off workflow
- It belongs in version control, shared with the team
- It's small enough to live as one topic file (~under 200 lines)

Redirect when:
- Procedural multi-step workflow Claude should execute on demand → `/build:build-skill`
- Lifecycle-event enforcement (pre-commit, pre-tool-use) → `/build:build-hook`
- A check is shell-expressible (grep, file existence, regex) → recommend a hook or linter
- Always-loaded global standards → consider `.claude/CLAUDE.md` instead — rules
  are right when the topic justifies its own file

### 1. Pick a Topic Name

Treat `$ARGUMENTS` as the user's topic. The filename becomes
`<topic>.md` under `.claude/rules/`. Use a descriptive, single-word
or hyphenated name like `testing.md`, `api-design.md`, `security.md`,
`code-style.md`. Subdirectories are allowed (e.g.,
`.claude/rules/frontend/components.md`).

If `$ARGUMENTS` is vague, propose 2–3 candidate filenames and let the
user pick.

### 2. Decide Scope

Two choices:

| Scope | Frontmatter | When to use |
|-------|-------------|-------------|
| **Always-on** | none | Project-wide standards (e.g., naming conventions, commit message format) |
| **Path-scoped** | `paths:` glob list | Rules that only apply when Claude works with specific files (e.g., backend rules in a monorepo) |

Anthropic's example for path-scoping:
```yaml
---
paths:
  - "src/api/**/*.ts"
---
```

Globs follow standard syntax. Brace expansion works:
`"src/**/*.{ts,tsx}"`. Multiple patterns are listed under one `paths:`
key.

### 3. Check for Conflicts

Read existing rules in `.claude/rules/` (and `~/.claude/rules/` if the
user maintains personal rules). Anthropic warns explicitly:

> "if two rules contradict each other, Claude may pick one arbitrarily"

Check for:
- Rules with overlapping `paths:` globs (or both global) covering the
  same convention
- Instructions that pull in opposite directions for the same scenario

If overlap found, ask: "This overlaps with `[existing rule]`. Merge,
replace, or keep both with explicit boundaries?"

### 4. Pick a Body Pattern

Decide which pattern fits the rule. Both are plain markdown — Anthropic
doesn't prescribe body structure beyond "specific over vague" and "use
markdown headers/bullets". The choice is toolkit-opinion guidance.

| Pattern | Use when | Body shape |
|---------|----------|------------|
| **Directive** (Anthropic's example pattern) | Rule tells Claude what to do; no judgment needed | Headers + bullet list of verifiable directives |
| **Enforcement** (toolkit-opinion structured shape) | Rule asks Claude to *judge* whether a file complies | `## Why` (failure cost + exception policy) → `## Compliant` example → `## Non-compliant` example |

Apply Anthropic's guidance to both:
- **Specific over vague.** "Use 2-space indentation" beats "Format code
  properly". Vague rules ("be clean", "be consistent") produce uneven
  adherence.
- **Markdown structure.** Headers and bullets group related instructions.
- **Size.** Target under 200 lines per rule file.
- **One topic per file.** A rule covering two unrelated conventions is
  two rules — split them.

For the **Enforcement pattern**, the structured `## Why` section
benefits from four components — see [rule-format-guide.md](references/rule-format-guide.md) → *Toolkit Recommendation: Structured Intent for Enforcement Rules* for the template, real-code example guidance, and default-closed declaration. These are toolkit-opinion conventions; they layer on top of the canonical primitive without introducing new frontmatter or required headings at the Anthropic-spec level.

### 5. Present for Approval

Before writing, narrate the design choices in 2–4 bullets:

- **Filename + location** — `.claude/rules/<name>.md` (or subdirectory
  path if used)
- **Scope** — always-on or path-scoped (and which globs)
- **Length and structure** — bullet list, headed sections, or
  example-driven; rough line count
- **What was skipped and why** — patterns considered but rejected

Show the complete file. Iterate on feedback. Hold the write until the
user approves.

### 6. Write the Rule

- Create `.claude/rules/` (and any subdirectory) if it doesn't exist
- Write the rule file at `.claude/rules/<name>.md`
- Report the file path

Claude Code picks up the new rule on the next session (always-on rules)
or the next time it reads a file matching `paths:` (scoped rules).

## Example

<example>
User: "I want a rule that staging dbt models only do casts, renames, and deduplication"

Assistant detects this as a backend / data-layer rule that should fire only
when Claude reads files in `models/staging/`. Picks filename
`staging-model-purity.md`. Checks `.claude/rules/` — no overlap.

Drafts:

```markdown
---
paths:
  - "models/staging/**/*.sql"
---

# Staging Model Purity

Staging models are a clean interface over raw sources. They must only:
- Cast types (`cast(... as date)`, `cast(... as integer)`)
- Rename columns (`select id as order_id, ...`)
- Deduplicate (`qualify row_number() over (partition by ...) = 1`)

## Why

Business logic in staging (revenue calculations, tier classifications)
couples source schema changes to business definitions. When either
changes, both layers need coordinated updates.

Exception: pure data-type normalization (e.g., parsing a date string
to a date type) is permitted.

## Compliant

```sql
-- models/staging/stg_orders.sql
select
  id as order_id,
  cast(order_date as date) as order_date,
  cast(quantity as integer) as quantity
from {{ source('raw', 'orders') }}
qualify row_number() over (partition by id order by _loaded_at desc) = 1
```

## Non-compliant

```sql
-- revenue calculation and tier classification are business logic
select id, quantity * unit_price as revenue,
  case when lifetime_value > 1000 then 'high' else 'standard' end as tier
from {{ source('raw', 'orders') }}
```
```

Narrates: filename `staging-model-purity.md`, path-scoped to
`models/staging/**/*.sql`, ~25 lines, example-driven structure (rule needs
LLM judgment so non-compliant/compliant pairs help). On approval, writes
to `.claude/rules/staging-model-purity.md`.
</example>

## Key Instructions

- Won't write a rule outside `.claude/rules/` — files at other paths are not loaded by Claude Code as rules. *(scope boundary)*
- Won't replace a traditional linter — if the request is syntax, formatting, import ordering, or naming case enforced by tooling, redirect to the appropriate linter and stop. *(scope boundary)*
- Default to always-on (no `paths:`) only for project-wide standards; reach for `paths:` when the rule is scoped to a directory or file type — unscoped rules consume context every session.
- Write specific, verifiable instructions ("Use 2-space indentation"), not vague ones ("format code properly") — vague rules produce uneven adherence.
- Run the conflict check (Step 3) before drafting — Anthropic warns that contradicting rules cause Claude to pick one arbitrarily.
- Hold the write until the user approves the drafted rule (Step 5 gate).
- Keep rules under 200 lines — split or move to a skill if they grow beyond that.

## Anti-Pattern Guards

1. **Rule outside `.claude/rules/`** — Claude Code only auto-loads rules from `.claude/rules/` (and `~/.claude/rules/`); files elsewhere are inert. Refuse to write to `docs/rules/` or other invented paths.
2. **Vague directive** ("be clean", "format properly") — restate in concrete, verifiable terms before accepting the rule.
3. **Convention enforceable by a traditional linter** (syntax, formatting, import ordering) — redirect to the linter and stop.
4. **Conflict check skipped** — run Step 3 before drafting; contradicting rules produce arbitrary behavior.
5. **Always-on rule that should be path-scoped** — flag rules whose content names a specific directory or file type but that omit `paths:`; the unscoped rule consumes context every session for content that only applies sometimes.

## Handoff

**Receives:** Topic name or description of the convention to capture (or no argument — assistant proposes a filename)
**Produces:** Rule file written to `.claude/rules/<name>.md` (or subdirectory)
**Chainable to:** check-rule (verify the new rule fits the existing library without conflicts)
