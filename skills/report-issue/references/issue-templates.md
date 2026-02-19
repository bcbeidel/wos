# Issue Templates

Templates for composing GitHub issues. Fill in the bracketed placeholders
with gathered context.

## Bug Report

```markdown
## Description

[What happened — clear, concise description of the bug]

## Minimum Reproducible Example

[The smallest possible setup that triggers the bug. Include:
- A minimal document fixture (inline or as a file description)
- The exact command or skill invocation
- The exact error output

If the bug requires multiple files, describe the minimal directory
structure needed to reproduce it.]

## Expected Behavior

[What should have happened]

## Actual Behavior

[What actually happened, including full error messages]

## Environment

- **wos version:** [version from plugin.json]
- **Python:** [python3 --version output]
- **Platform:** [uname output]
```

## Feature Request

```markdown
## Problem

[Describe the problem generically — any WOS user should recognize it.
Avoid references to specific vaults, file counts, or personal workflows.]

## Why This Matters

[1-3 bullet points on impact: who is affected, what breaks or degrades,
why the current state is insufficient. Frame from the tool's perspective.]

## Proposed Solution

[What the feature does and how it works. Include before/after examples
where behavior changes. Include design decisions for non-obvious choices.]

### Scope

[What's included in this proposal.]

### Non-Goals

[What's explicitly excluded to prevent scope creep.]

## Evaluation

### Test Fixtures

[Minimal example files or scenarios that demonstrate the expected behavior.
Each fixture should test one specific aspect.]

| Fixture | Scenario | Expected result |
|---|---|---|
| [file/scenario] | [what it tests] | [pass/fail criteria] |

### Pass Criteria

[Measurable outcomes. How do we know this works?]

| Test | Expected result |
|---|---|
| [specific test] | [specific expected outcome] |

## Alternatives Considered

[Other approaches and why they're less suitable.]

## Environment

- **wos version:** [version from plugin.json]
```

## General Feedback

```markdown
## Context

[What were you doing when this observation came up?]

## Observation

[What did you notice? What could be better?]

## Suggestion

[Any ideas for improvement]

## Environment

- **wos version:** [version from plugin.json]
```
