# Principle Structure

## File Format

`PRINCIPLES.md` lives at the repo root with no frontmatter — it is a
constitutional document loaded via `@PRINCIPLES.md`, not a WOS context file.

```markdown
# Principles

[Optional 1-2 sentence preamble about the project's philosophy]

## [Principle Name]
[One-sentence statement describing the desired outcome]

**Rationale:** [Why this principle matters for this project]
**Boundary:** [When this principle doesn't apply or should yield]
**Verification:** [Concrete way to check compliance — not a vague aspiration]
```

## Authoring Criteria

Each principle should satisfy at least 3 of these 5 criteria:

1. **Outcome-focused** — states a desired quality, not a procedure
2. **Testable** — can be evaluated as satisfied or violated in specific code
3. **Rationale-based** — there's a documentable "why" behind it
4. **Stable** — wouldn't change if you swapped frameworks or languages
5. **Ambiguity-scoped** — guides choices when multiple valid approaches exist

Candidates passing 0-2 criteria are rules or preferences, not principles.

## Component Guidelines

### Name
Short, memorable phrase. Imperative or noun form. No numbering — principles
aren't ranked.

Examples: "Convention over configuration", "Bottom line up front",
"Depend on nothing"

### Statement
One sentence. Describes the desired outcome or behavior. Stands alone
without the rationale.

Good: "Document patterns, don't enforce them."
Bad: "We should try to document patterns when possible."

### Rationale
Why this principle exists for *this project*. Not a generic argument — tie
it to the project's specific context, constraints, or history.

### Boundary
When this principle doesn't apply or should yield to another concern.
Every principle has limits. If you can't articulate a boundary, the
principle may be too vague.

Good: "When safety-critical behavior requires enforcement, use hooks
instead of documentation."
Bad: "Sometimes this doesn't apply."

### Verification
A concrete way to check whether code or decisions comply. The research
finding: principles with embedded verification criteria outperform pure
declarative principles.

Good: "No class inherits more than one concrete class."
Good: "Every script runs via `uv run` with PEP 723 metadata."
Bad: "Code should feel simple."

## Density Guidance

| Count | Assessment |
|-------|-----------|
| 3-10 | Healthy range for reliable agent adherence |
| 11-15 | Review whether some items are rules or preferences |
| 16+ | Agents likely to drop or conflate principles — consolidate |

Research basis: ~150-200 effective instructions per agent session, with
system prompts consuming roughly a third. Principles compete for the
remaining attention budget.
