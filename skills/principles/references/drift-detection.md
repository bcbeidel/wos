# Drift Detection

How to detect when practice has diverged from stated principles on
re-runs of the principles skill.

## When to Use

This workflow runs when `PRINCIPLES.md` already exists. The skill loads
current principles and scans for three types of drift.

## Drift Types

### A. New Implicit Principles

Patterns in artifacts not yet captured in `PRINCIPLES.md`:

- New CLAUDE.md sections that read like principles (apply the five-criteria
  filter from the extraction heuristics reference)
- Recurring rationale in commits/PRs since `PRINCIPLES.md` was last
  modified (check git log with `--after` date filter)
- Code patterns suggesting unstated conventions not captured as principles

### B. Stale Principles

Principles in `PRINCIPLES.md` no longer reflected in practice:

- Code patterns that consistently violate a stated principle
- CLAUDE.md rules that contradict a principle
- Recent commits that actively work against a principle

A single violation does not make a principle stale — look for a pattern
of 3+ instances suggesting the team has moved on.

### C. Principle Evolution

Principles where wording no longer matches how the team applies them:

- Boundary cases that have shifted (the exception became the norm)
- Verification criteria that no longer make sense given current tooling
- The spirit is still followed but the letter has drifted

## Scan Process

1. Read `PRINCIPLES.md` and build an inventory: name, statement,
   verification criteria for each principle
2. Check the last-modified date of `PRINCIPLES.md` via git log
3. Scan CLAUDE.md and AGENTS.md for new principle-like content
4. Scan recent commits since last modification (~50 or since last
   modified, whichever is fewer)
5. Sample key code files for patterns that confirm, contradict, or
   extend existing principles
6. Classify each finding as type A, B, or C

## Presentation Format

Present a drift report with three sections:

```
## Drift Report

### New candidates (not yet captured)
| # | Candidate | Source | Confidence |
|---|-----------|--------|------------|

### Potentially stale
| # | Principle | Evidence | Confidence |
|---|-----------|----------|------------|

### Wording drift
| # | Principle | Current | Suggested Revision | Evidence |
|---|-----------|---------|-------------------|----------|

No changes needed: N of M principles remain current.
```

Each proposed change is independent — user approves, rejects, or edits
per item. New candidates go through the full articulation process
(name, statement, rationale, boundary, verification).

## Confidence for Drift Findings

- **HIGH** — 5+ instances of consistent pattern across multiple sources
- **MODERATE** — 2-4 instances or pattern in a single source type
- **LOW** — 1 instance, possibly incidental

Present LOW confidence findings separately, clearly marked as
"possible drift — may not warrant action."
