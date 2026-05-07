---
name: check-help-skill
description: >-
  Use when the user wants to "audit a help skill", "review my plugin
  index", or "verify my help-skill is up to date". Audits a
  plugins/<plugin>/skills/help/SKILL.md against the help-skill rubric
  — coverage, freshness, frontmatter fidelity, plus five judgment
  dimensions and a trigger-collision check.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path to help-skill SKILL.md, or plugin name]"
user-invocable: true
version: 1.0.0
owner: build-plugin
license: MIT
references:
  - ../../_shared/references/help-skill-best-practices.md
  - ../../_shared/references/skill-best-practices.md
  - references/check-dual-audience.md
  - references/check-scope-discipline.md
  - references/check-triage-scaffolding.md
  - references/check-trigger-collision.md
  - references/check-trigger-quality.md
  - references/check-workflow-curation.md
---

# /build:check-help-skill

Audit a help-skill — the SKILL.md at
`plugins/<plugin>/skills/help/SKILL.md` — against the rubric in
[help-skill-best-practices.md](../../_shared/references/help-skill-best-practices.md).

This skill follows the [check-skill
pattern](../../_shared/references/check-skill-pattern.md). Tier-1 is
deterministic via `scripts/check_help_skill.py` (17 rule_ids; emits a
JSON array of envelopes via `_common.py`). Tier-2 has 5 judgment
dimensions read inline by the primary agent. Tier-3 is the
trigger-collision cross-entity rule.

## When to use

Also fires when the user phrases the request as:

- "check the /<plugin>:help command"
- "is the skill table in this help-skill current"

## Workflow

### 1. Resolve the target

Read `$ARGUMENTS`. If it ends in `SKILL.md`, treat as the path. If it
names a plugin (e.g., `work`), resolve to
`plugins/<plugin>/skills/help/SKILL.md`. If the file does not exist,
stop — there is nothing to audit (recommend `/build:build-help-skill
<plugin>`). If the path resolves to a SKILL.md whose `name` is not
`help`, stop and route to `/build:check-skill`.

### 2. Tier-1 deterministic checks

Invoke the script:

```bash
python3 plugins/build/skills/check-help-skill/scripts/check_help_skill.py <plugin-or-path>
```

Parse stdout as JSON. The script emits an array of 17 envelopes — one
per rule_id, regardless of which fired. Each envelope:
`{rule_id, overall_status, findings[]}`, with each finding carrying
`{status, location, reasoning, recommended_changes}`.
`recommended_changes` is canonical — copy through verbatim to the report.

**Rule set** (17 Tier-1 rules):

| Severity | rule_id |
|---|---|
| fail | `slug-mismatch` |
| warn | `frontmatter-shape` |
| warn | `frontmatter-invented-key` |
| warn | `body-line-count` |
| fail | `secret` |
| fail | `tls-disable` |
| fail | `pipe-to-shell` |
| warn | `synopsis-present` |
| fail | `managed-region-present` |
| fail | `skill-index-coverage` |
| warn | `skill-index-no-self` |
| warn | `description-fidelity` |
| warn | `workflow-section-present` |
| warn | `workflow-freshness` |
| warn | `pointer-resolution` |
| fail | `pointer-broken-fail` |
| warn | `description-trigger-shape` |

Exit codes: `0` if no envelope is `fail`; `1` if any envelope is
`fail`; `64` on argument error.

**Tier-2 exclusion list.** Any `slug-mismatch`, `secret`,
`tls-disable`, `pipe-to-shell`, `managed-region-present`,
`skill-index-coverage` (rows for skills that don't exist on disk), or
`pointer-broken-fail` finding excludes the file from Tier-2 — fix the
structural issue before evaluating quality. Other FAILs surface and
allow Tier-2 to proceed.

### 3. Tier-2 judgment dimensions

For each file that passed the Tier-2 exclusion gate, evaluate against
the **5 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-workflow-curation.md](references/check-workflow-curation.md) | D1 — `## Common workflows` carries composed chains | warn |
| [check-triage-scaffolding.md](references/check-triage-scaffolding.md) | D2 — task → skill mapping is actionable | warn |
| [check-dual-audience.md](references/check-dual-audience.md) | D3 — readable for both human and agent audiences | warn |
| [check-scope-discipline.md](references/check-scope-discipline.md) | D4 — stays inside (synopsis, index, workflows, pointers) | warn |
| [check-trigger-quality.md](references/check-trigger-quality.md) | D5 — fires on meta-questions, not the plugin's own workflows | warn |

#### Evaluator policy

- **Single locked-rubric pass.** Read all 5 rule files first, then
  evaluate the help-skill against the unified rubric. A single
  locked-rubric pass produces stable scoring.
- **Default-closed when borderline.** When evidence is ambiguous,
  return `warn`, not `pass`.
- **Severity floor: WARN.** All 5 Tier-2 dimensions are coaching, not
  blocking. Escalate to FAIL only for safety concerns Tier-1 missed.
- **One finding per dimension maximum.** If a single hook trips one
  dimension at multiple locations, surface the highest-signal one.

### 4. Tier-3 cross-entity trigger collision

Evaluate against
[check-trigger-collision.md](references/check-trigger-collision.md).
For every sibling skill in the plugin, compare its `description`
against the help-skill's `description`. The rule documents two
heuristics: token overlap (shared trigger-phrase tokens above
threshold; `info` at 3+, `warn` at 5+) and identical trigger phrasing
(`warn`).

This is the **load-bearing** dimension — a help-skill in isolation
can pass Tier-1 and Tier-2 cleanly while being fundamentally broken
when the router has to pick between it and a colliding sibling.
Skipping Tier-3 leaves the highest-value defect undetected.

### 5. Report

Merge Tier-1 (script JSON) + Tier-2 (judgment) + Tier-3 (judgment)
findings into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2
before Tier-3 within severity. Summary line at top and bottom: `N
fail, N warn across N rules`. If any envelope is `fail` and excludes
Tier-2, name the trigger.

For each finding's `Recommendation:` line, copy `recommended_changes`
through verbatim. Multi-paragraph recipes condense to the first
paragraph in the report; the full recipe is presented in the repair
loop.

### 6. Opt-in repair loop

Ask exactly once:

> "Apply fixes? Enter `y` (all), `n` (skip), or comma-separated
> finding numbers."

For each selected finding, route per the recipe in
`recommended_changes`:

- **Direct edit** — frontmatter shape, slug, synopsis, pointer
  resolution, description rewrite. Show diff; write on confirmation.
- **Routed to another skill** — `/build:build-help-skill <plugin>`
  (rebuild from scratch when the file is too damaged); table
  regeneration is typically delegated to the plugin's
  `build-help-skill` render script.
- **Tier-2/3 judgment** — workflow curation, scope discipline, trigger
  collision. Ask the user; rewrite the section/description; show
  diff; write on confirmation.

After each applied fix, re-run the Tier-1 script (or re-judge the
Tier-2/3 dimension) on the affected scope so subsequent findings
reflect the new state. Terminate when the user enters `n` or
exhausts findings.

## Anti-Pattern Guards

1. **Skipping the trigger-collision check.** A help-skill that
   parses cleanly but collides with siblings will misroute callers
   silently. Tier-3 is the load-bearing dimension; running only
   Tier-1 + Tier-2 leaves the highest-value defect undetected.
2. **Auto-repairing Tier-2 findings.** Judgment dimensions
   (workflow curation, dual audience, scope discipline) need user
   input. Auto-applying recipes without confirmation produces
   plausible but wrong rewrites.
3. **Treating description-fidelity as deterministic-equivalent.**
   The check compares the table's trigger column to the sibling's
   current description; minor wording differences are expected
   (truncation to ~12 words). The check fires on *substantive*
   drift (a sibling description changed and the table did not).
4. **Inlining a chained skill instead of invoking it.** MUST invoke
   `/build:check-skill` via the Skill tool when Step 1 routes
   off-target.
5. **Re-evaluating scripted rules in Tier-2.** The script is
   authoritative for the 17 Tier-1 rules; trust the `pass` envelope.
6. **Suppressing the inapplicable envelope.** When a sibling SKILL.md
   cannot be read (malformed frontmatter), the affected coverage /
   fidelity rule emits inapplicable — surface it; do not silently skip.
7. **Embellishing scripts' recommended_changes.** Each rule's recipe
   constant is canonical guidance sourced from
   `help-skill-best-practices.md`. Copy it through; do not paraphrase.

## Key Instructions

- Run Tier-1 before Tier-2; the FAIL exclusion list above gates
  judgment evaluation.
- Cite the source principle for every finding — every rule's body
  names the `help-skill-best-practices.md` section it enforces.
- Tier-3 (trigger-collision) is load-bearing — never skip.
- Repair is opt-in and per-finding; never apply recipes without
  explicit user confirmation.
- Recovery: read-only outside the Repair Loop; edits revertable via
  `git diff` / `git checkout`.

## Handoff

**Receives:** Path to a help-skill SKILL.md or a plugin name.

**Produces:** A unified findings table merging the 17 Tier-1
envelopes (script JSON), 5 Tier-2 judgment findings, and the Tier-3
trigger-collision finding. Each row: tier, rule_id, location, status,
reasoning + recommended_changes excerpt. Optionally — per user
confirmation in the Repair Loop — targeted edits to the help-skill
SKILL.md.

**Chainable to:** `/build:check-skill <path>` (catches generic
SKILL.md structural issues outside the help-skill rubric);
`/build:check-skill-pair help-skill` (audits pair-level integrity);
`/build:build-help-skill <plugin>` (when the target file does not
exist or is too damaged for repair).
