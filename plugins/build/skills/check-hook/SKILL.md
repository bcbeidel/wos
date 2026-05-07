---
name: check-hook
description: >
  Audits Claude Code hooks configuration for event coverage, script
  safety, async and blocking contradictions, Stop hook loop risks,
  rule overlap, and idempotency. Use when the user wants to "audit
  hooks", "check hooks", "review hooks", "check my hooks", "what
  quality gates are missing", or "are my hooks safe".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[settings.json path]"
user-invocable: true
references:
  - ../../_shared/references/brief-best-practices.md
  - ../../_shared/references/hook-best-practices.md
  - references/check-async-blocking-coherence.md
  - references/check-attack-surface.md
  - references/check-brief-presence-and-content.md
  - references/check-claude-md-overlap.md
  - references/check-command-path-expansion.md
  - references/check-destructive-operations.md
  - references/check-event-matcher-fit.md
  - references/check-exit-code-contract.md
  - references/check-idempotency.md
  - references/check-injection-safety.md
  - references/check-jq-handling.md
  - references/check-json-output-contract.md
  - references/check-latency.md
  - references/check-primitive-routing-coverage.md
  - references/check-shell-hygiene.md
  - references/check-static-analysis.md
  - references/check-stdin-consumption.md
  - references/check-stop-loop-guard.md
  - references/platform-limitations.md
license: MIT
---

# Check Hook

Audit a project's Claude Code hooks configuration against the rubric
in
[hook-best-practices.md](../../_shared/references/hook-best-practices.md).
Read-only until the opt-in Repair Loop.

This skill follows the [check-skill
pattern](../../_shared/references/check-skill-pattern.md). It is a
**pure-judgment skill** — no Tier-1 detection scripts of its own; the
18 rules live as `references/check-*.md` files read inline by the
primary agent during Tier-2. Tier-3 (cross-entity collision) does not
apply (single configuration scope per audit).

## Workflow

1. Scope → 2. Tier-2 Judgment → 3. Platform Scope → 4. Report → 5. Opt-In Repair Loop.

### 1. Scope

If `$ARGUMENTS` is non-empty, read the settings file at that path.
Otherwise, read from both default locations (use whichever exist):

- `.claude/settings.json`
- `.claude/settings.local.json`

If neither exists, or neither has a `hooks:` key, the first finding
is:

> **No hooks configured** (warn) — PreToolUse hooks provide
> deterministic enforcement CLAUDE.md instructions cannot guarantee.

The `check-primitive-routing-coverage` rule (Tier-2 below) will also
fire if `CLAUDE.md` carries advisory rules that should be hooks.

### 2. Tier-2 Judgment

Evaluate each configured hook against the **18 judgment rules** in
`references/check-*.md`. Read each rule body once, then evaluate
every hook against it as a unified rubric pass.

The 18 dimensions:

| File | Dimension | Severity |
|---|---|---|
| [check-event-matcher-fit.md](references/check-event-matcher-fit.md) | Event-matcher fit (right event, canonical casing, matcher syntax) | fail |
| [check-exit-code-contract.md](references/check-exit-code-contract.md) | Exit code contract (`exit 2` for blocks; explicit Python handlers) | fail |
| [check-stdin-consumption.md](references/check-stdin-consumption.md) | Stdin consumption (`INPUT=$(cat)`; executable bit) | warn |
| [check-json-output-contract.md](references/check-json-output-contract.md) | JSON output contract (exit-0 only; `hookEventName`; <10 KB) | warn |
| [check-async-blocking-coherence.md](references/check-async-blocking-coherence.md) | Async-blocking coherence (no `async: true` + `exit 2`) | fail |
| [check-command-path-expansion.md](references/check-command-path-expansion.md) | Command path expansion (`$CLAUDE_PROJECT_DIR`, never `$HOME`/`~`) | warn |
| [check-stop-loop-guard.md](references/check-stop-loop-guard.md) | Stop-loop guard (re-entry guard for blocking Stop / SubagentStop) | fail |
| [check-destructive-operations.md](references/check-destructive-operations.md) | Destructive operations (no `rm -rf`, `git reset --hard`, `git push --force`) | fail |
| [check-injection-safety.md](references/check-injection-safety.md) | Injection safety (no `eval` on payload; quoted expansions) | fail/warn |
| [check-jq-handling.md](references/check-jq-handling.md) | jq handling (availability, field paths, cross-platform) | fail/warn |
| [check-shell-hygiene.md](references/check-shell-hygiene.md) | Shell hygiene (`set -Eeuo pipefail`, output routing, `[[`) | warn |
| [check-attack-surface.md](references/check-attack-surface.md) | Attack surface (CVE-2025-59536-aware placement) | warn |
| [check-latency.md](references/check-latency.md) | Latency (under 1s synchronous; no recursive `claude` invocation) | fail/warn |
| [check-idempotency.md](references/check-idempotency.md) | Idempotency (running twice produces same outcome) | warn |
| [check-static-analysis.md](references/check-static-analysis.md) | Static analysis (ShellCheck and `shfmt` integration) | warn |
| [check-claude-md-overlap.md](references/check-claude-md-overlap.md) | CLAUDE.md overlap (surface for user; never auto-resolve) | warn |
| [check-brief-presence-and-content.md](references/check-brief-presence-and-content.md) | Brief presence + content (5 H2 sections; specific *So-what*) | warn |
| [check-primitive-routing-coverage.md](references/check-primitive-routing-coverage.md) | CLAUDE.md → hook conversion candidates | warn |

#### Evaluator policy

- **Single locked-rubric pass per hook.** Read all 18 rule files
  first, then evaluate each hook in turn against the unified rubric.
  A single locked-rubric pass stabilizes severity.
- **Default-closed when borderline.** When evidence is ambiguous,
  return `warn`, not `pass`.
- **Severity floor: WARN.** Most dimensions are coaching, not
  blocking. Escalate to FAIL only for the 7 rules whose severity is
  documented as `fail` (event-matcher-fit, exit-code-contract,
  async-blocking-coherence, stop-loop-guard, destructive-operations,
  injection-safety, jq-handling for Copilot field-path mismatch,
  latency for recursive `claude` invocation).
- **One finding per dimension per hook maximum.** If a single hook
  trips one dimension at multiple locations, surface the
  highest-signal location with concrete detail. Bulk findings train
  the user to disregard the audit.

For each finding, capture: dimension name, offending hook / command /
file, specific issue, severity. The finding's `recommended_changes`
copies through from the rule body's *How to apply* section + example.

### 3. Platform Scope

These checks target Claude Code (`settings.json` /
`settings.local.json`). If the project's hooks may run on additional
platforms beyond Claude Code, read
[platform-limitations.md](references/platform-limitations.md) and
append platform-specific findings as a separate report section.

### 4. Report

Present findings as a summary count plus a table, severity-sorted
(`fail` → `warn` → `inapplicable`):

```
N issues across M hooks (X fail, Y warn)

event          | hook command          | dimension                 | finding
---------------+-----------------------+---------------------------+---------------------------
PostToolUse    | .claude/hooks/gate.sh | event-matcher-fit         | PostToolUse cannot block; use PreToolUse
Stop           | .claude/hooks/stop.sh | stop-loop-guard           | No re-entry guard — infinite loop risk
PostToolUse    | lint-after-write.sh   | async-blocking-coherence  | async:true + exit 2 — never blocks
```

If Platform Scope added findings, append:

```
**Cross-platform limitations:** [list per platform]
```

If no issues: "Hooks look well-configured."

### 5. Opt-In Repair Loop

Ask exactly once:

> "Apply fixes? Enter `y` (all), `n` (skip), or comma-separated
> numbers."

For each selected finding, route per the recipe in
`recommended_changes` (the rule body's *How to apply* section + code
example). Most fixes fall into three buckets:

- **Direct edit** — add `INPUT=$(cat)`, fix matcher casing, swap
  `$HOME` for `$CLAUDE_PROJECT_DIR`, add `set -Eeuo pipefail`. Show
  diff; write on confirmation.
- **Routed to another skill** — substantive rewrites (event must
  change; new hook needed for primitive-routing-coverage finding) →
  recommend `/build:build-hook`. Pair-level integrity issues →
  recommend `/build:check-skill-pair hook`.
- **Requires user judgment** — `claude-md-overlap` (keep both vs.
  drop one), `attack-surface` placement decisions, intentional
  advisory rules from `primitive-routing-coverage`.

Show the diff before writing. Terminate when the user selects no
further findings, enters `n`, or confirms `done`.

## Anti-Pattern Guards

1. **Treating rule overlap as always wrong.** CLAUDE.md + hook
   duplication can be intentional belt-and-suspenders; flag for user
   decision, do not auto-remove.
2. **Skipping `check-primitive-routing-coverage` when no hooks
   exist.** Absence of hooks is itself a coverage gap worth
   surfacing — the rule fires regardless of the configured-hook count.
3. **Reading settings outside the project.** Only
   `.claude/settings.json` and `.claude/settings.local.json` under
   the current project root, unless the user passes an explicit path.
4. **Bulk-applying fixes.** Per-finding confirmation required. Some
   findings (CLAUDE.md overlap, blocking-before-warn graduation) are
   intentional mid-deployment states.
5. **Re-evaluating Tier-2 rules across multiple passes.** Each
   judgment dimension is one finding maximum per hook; resist the
   urge to re-score against the same rule for "another angle".
6. **Suppressing the inapplicable case.** When a rule does not apply
   (e.g., `stop-loop-guard` against a `PreToolUse` hook), return
   `inapplicable` silently — do not pad the report with "N/A" rows.
7. **Embellishing rule body wording in the report.** Each rule's
   *How to apply* + example is canonical guidance. Copy it through
   for `recommended_changes`; do not paraphrase or expand.

## Key Instructions

- Read-only until the Repair Loop; no writes without per-finding
  confirmation.
- The `check-primitive-routing-coverage` rule fires whether or not
  hooks are configured — absence of hooks against a CLAUDE.md
  carrying convertible rules is the coverage gap it surfaces.
- `stop-loop-guard` findings are `fail`, not `warn` — unguarded
  blocking Stop hooks require a session kill to recover.
- 18 judgment dimensions evaluated per hook; a dimension that does
  not apply (e.g., a rule about Python hooks against a bash hook)
  returns `inapplicable` silently.
- Recovery: outside the Repair Loop this skill modifies nothing; any
  edits it produces can be reverted with `git diff` / `git checkout`.

## Handoff

**Receives:** Settings file path (optional); defaults to
`.claude/settings.json` and `.claude/settings.local.json`.

**Produces:** A unified findings table merging the 18 judgment
dimensions plus optional platform-specific findings. Each row carries
the dimension, hook command, finding, severity, and a
`recommended_changes` excerpt from the rule body. Optionally — per
user confirmation in the Repair Loop — targeted edits to settings
files or hook scripts.

**Chainable to:** `/build:build-hook` (create a new hook or
substantially rewrite one flagged by the audit);
`/build:check-skill-pair hook` (audit pair-level integrity).
