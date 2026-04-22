---
name: build-rule
description: Create a Claude Code rule under `.claude/rules/` — a markdown instruction file with optional `paths:` frontmatter for path-scoping. Use when the user wants to "create a rule", "build a rule", "add a rule", "capture this convention", or "enforce this pattern".
argument-hint: A topic name or description of the convention to capture
user-invocable: true
references:
  - ../../_shared/references/primitive-routing.md
  - ../../_shared/references/rule-canonical-form.md
  - ../../_shared/references/rule-structured-intent.md
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

Frontmatter shape, multi-pattern / brace-expansion syntax, and glob
reference: see the `rule-canonical-form.md` reference listed in
frontmatter.

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

Decide which pattern fits the rule — a toolkit-opinion choice layered
on top of Anthropic's canonical spec:

| Pattern | Use when |
|---------|----------|
| **Directive** (Anthropic's example pattern) | Rule tells Claude what to do; no judgment needed. Body conventions: [rule-canonical-form.md → Body Conventions](../../_shared/references/rule-canonical-form.md#body-conventions). |
| **Enforcement** (toolkit-opinion structured shape) | Rule asks Claude to *judge* whether a file complies. Template, four-component `## Why`, example-pair guidance, and default-closed declaration: [rule-structured-intent.md](../../_shared/references/rule-structured-intent.md). |

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
User: "I want a rule that staging dbt models only do casts, renames, and deduplication."

Assistant recognizes the rule asks Claude to *judge* whether a staging
model complies — an **enforcement-pattern** rule, path-scoped to
`models/staging/**/*.sql`. Picks filename `staging-model-purity.md`;
scans `.claude/rules/` for overlap (none). Narrates the design:

- Filename + location: `.claude/rules/staging-model-purity.md`
- Scope: path-scoped, `models/staging/**/*.sql`
- Structure: enforcement pattern — `## Why` (failure cost + exception),
  `## Compliant` / `## Non-compliant` SQL pair drawn from real staging
  models, plus the default-closed declaration
- What was skipped: directive-only body — the rule needs LLM judgment
  against real SQL, so the example pair carries its weight

Shows the complete draft (following the template in
`rule-structured-intent.md`) and holds the write until the user approves.
</example>

## Key Instructions

- Won't write a rule outside `.claude/rules/` — files at other paths are not loaded by Claude Code as rules. *(scope boundary)*
- Won't replace a traditional linter — if the request is syntax, formatting, import ordering, or naming case enforced by tooling, redirect to the appropriate linter and stop. *(scope boundary)*
- Run the conflict check (Step 3) before drafting — Anthropic warns that contradicting rules cause Claude to pick one arbitrarily.
- Hold the write until the user approves the drafted rule (Step 5 gate).

## Anti-Pattern Guards

1. **Rule outside `.claude/rules/`** — Claude Code only auto-loads rules from `.claude/rules/` (and `~/.claude/rules/`); files elsewhere are inert. Refuse to write to `docs/rules/` or other invented paths.
2. **Convention enforceable by a traditional linter** (syntax, formatting, import ordering) — redirect to the linter and stop.
3. **Conflict check skipped** — run Step 3 before drafting; contradicting rules produce arbitrary behavior.
4. **Writing before approval** — hold the write until Step 5 approval; the review gate is where design errors surface.

## Handoff

**Receives:** Topic name or description of the convention to capture (or no argument — assistant proposes a filename)
**Produces:** Rule file written to `.claude/rules/<name>.md` (or subdirectory)
**Chainable to:** check-rule (verify the new rule fits the existing library without conflicts)
