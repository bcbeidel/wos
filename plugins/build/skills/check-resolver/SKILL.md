---
name: check-resolver
description: Audit a root-level resolver — verify AGENTS.md pointer, managed-region integrity, filing-table coverage against disk, context-table actionability, and trigger-eval pass rate. Use when the user wants to "audit a resolver", "check RESOLVER.md", "validate routing table", "find dark capabilities", or "are my filing rules current".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[target directory — defaults to CWD; walks up to the nearest RESOLVER.md and audits that one]"
user-invocable: true
references:
  - ../../_shared/references/brief-best-practices.md
  - ../../_shared/references/resolver-best-practices.md
  - references/check-brief-presence-and-content.md
  - references/check-context-actionability.md
  - references/check-eval-representativeness.md
  - references/check-filing-coverage.md
license: MIT
---

# /build:check-resolver

Evaluate a root-level resolver in three tiers: deterministic artifact and path checks (no LLM), per-dimension semantic evaluation (one locked-rubric LLM call), and cross-artifact reachability + staleness against disk state.

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 3 scripts emitting JSON envelopes via `_common.py` (11 rule_ids total). Tier-2 has 4 judgment dimensions read inline by the primary agent. Tier-3 cross-artifact checks are mechanized as Tier-1 rule_ids (`dark-capability`) or opt-in (`--run-evals`).

The audit rubric mirrors the authoring principles in [resolver-best-practices.md](../../_shared/references/resolver-best-practices.md). When the principles doc changes, the dimensions follow.

## Workflow

### 1. Discover Resolver Artifacts

Walk up from the target directory looking for `RESOLVER.md`. The first ancestor with one becomes the **resolver root**; all checks scope to that resolver and its subtree.

Locate three artifacts at the resolver root:
- `RESOLVER.md`
- `AGENTS.md` (for the pointer check)
- `.resolver/evals.yml` (sibling to RESOLVER.md)

Report: "Found resolver at `<resolver root>`. Auditing N filing rows, M context rows, K eval cases."

If no `RESOLVER.md` is found anywhere up to the filesystem root, emit FAIL and stop — nothing to audit. To audit every resolver in a repo with nested resolvers, run this skill once per resolver root.

### 2. Tier-1 Deterministic Checks

Invoke the three detection scripts:

```bash
python3 plugins/build/skills/check-resolver/scripts/check_pointer.py <resolver-root>
python3 plugins/build/skills/check-resolver/scripts/check_resolver.py <resolver-root>
python3 plugins/build/skills/check-resolver/scripts/check_evals.py <resolver-root>
```

Each script emits a JSON array of envelopes. Parse stdout per script. The combined Tier-1 rule set:

**Script-to-rules map** (11 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_pointer.py` | `pointer-present` | fail |
| `check_pointer.py` | `pointer-resolves` | fail |
| `check_resolver.py` | `markers-present` | fail |
| `check_resolver.py` | `filing-paths-resolve` | fail |
| `check_resolver.py` | `context-paths-resolve` | fail |
| `check_resolver.py` | `filing-rows-unique` | fail |
| `check_resolver.py` | `context-rows-unique` | fail |
| `check_resolver.py` | `dark-capability` | warn |
| `check_resolver.py` | `mtime-stale` | warn |
| `check_evals.py` | `evals-parse` | fail |
| `check_evals.py` | `eval-pass-stale` | warn |

Each finding's `recommended_changes` is canonical — copy it through verbatim. `recommended_changes` is REQUIRED on every finding.

**Tier-2 exclusion list.** Any FAIL in `pointer-present`, `pointer-resolves`, `markers-present`, `filing-paths-resolve`, `context-paths-resolve`, `filing-rows-unique`, `context-rows-unique`, or `evals-parse` excludes the resolver from Tier-2 — a malformed or unreachable resolver shouldn't burn LLM budget.

**WARN findings (`dark-capability`, `mtime-stale`, `eval-pass-stale`)** never exclude. They surface alongside Tier-2 findings.

### 3. Tier-2 Judgment Dimensions

For resolvers that passed the Tier-2 exclusion gate, evaluate against the **4 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-filing-coverage.md](references/check-filing-coverage.md) | D1 — every depth-1 directory classified (filing / context / out-of-scope / ambient / delegated) | warn |
| [check-context-actionability.md](references/check-context-actionability.md) | D2 — context rows list 1-4 concrete entries, not vague prose | warn |
| [check-eval-representativeness.md](references/check-eval-representativeness.md) | D3 — evals exercise both filing/context routing; ≥1 case per filing row; ≥15% negative | warn |
| [check-brief-presence-and-content.md](references/check-brief-presence-and-content.md) | D4 — `.briefs/<slug>.brief.md` exists with 5 H2s; *So-what* is specific | warn |

#### Evaluator policy

- **Single locked-rubric pass.** Read all 4 rule files first, then evaluate the resolver in one LLM call against the unified rubric. A single locked-rubric pass produces stable scoring.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`, not `pass`.
- **Severity floor: WARN.** All 4 Tier-2 dimensions are coaching, not blocking. Escalate to FAIL only for safety concerns Tier-1 missed.
- **One finding per dimension maximum.** Surface the highest-signal location with concrete excerpts.

Include `RESOLVER.md` verbatim in the Tier-2 prompt — never summarize. Include the directory scan output, `.resolver/evals.yml`, and `.briefs/<slug>.brief.md` (if present).

### 4. Tier-3 Cross-Artifact Checks

**Dark-capabilities scan.** Mechanized as Tier-1 `dark-capability` (already part of `check_resolver.py`'s output). For every directory under the resolver root (depth 1–2), classify as: in-filing, in-context, in-out-of-scope, ambient (`.git`, `node_modules`, `dist`, `build`, `.cache`, `.venv`, `target`, `__pycache__`, `.resolver`), or delegated (nested `RESOLVER.md`). Anything unclassified surfaces as `warn`. Subdirectories of a filing dir are not auto-classified.

**Managed-region drift.** Currently judgment-evaluated as part of D1 (filing-coverage). Future work could mechanize as a separate Tier-3 rule that diffs the live managed region against a fresh regeneration.

**Optional: `--run-evals`.** When invoked with `--run-evals`, execute each case in `.resolver/evals.yml` against a Claude call with RESOLVER.md in context. Each failing case surfaces as a Tier-3 finding. This step is opt-in (slow and costs LLM calls).

### 5. Report Findings

Merge findings from all three sources (3 detection scripts' JSON envelopes + 4 Tier-2 judgment findings + optional `--run-evals` results) into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3 within severity. Each finding's `Recommendation:` line copies through `recommended_changes` verbatim.

Close with:
- `Resolver audited — no findings` or
- `Resolver audited, N findings (X fail, Y warn)`

### 6. Opt-In Repair Loop

Ask exactly once:

> "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding, route per the recipe in `recommended_changes`:

- **Direct edit** — managed-region row corrections, AGENTS.md pointer text, eval-pass timestamp refresh. Show diff; write on confirmation.
- **Routed to another skill** — large structural drift → `/build:build-resolver --regenerate`; missing filing rows → `/build:build-resolver --add-filing <type>`.
- **Tier-2 judgment** — filing coverage, context actionability, eval representativeness, brief content quality. Ask the user; rewrite the section; show diff; write on confirmation.

After each applied fix, re-run the affected Tier-1 script (or re-judge the Tier-2 dimension). Terminate when the user enters `n` or exhausts findings.

## Anti-Pattern Guards

1. **LLM-evaluating path existence.** Path existence is Tier-1's job (deterministic file checks); paths either resolve or they don't.
2. **Per-dimension Tier-2 calls.** Use one locked-rubric call per resolver — a unified rubric produces stable scoring.
3. **Hand-managed region edits treated as valid.** Any row in the managed region that doesn't regenerate from disk is drift — FAIL or WARN depending on whether the row still resolves.
4. **Reporting without recommendations.** Every finding's `recommended_changes` is canonical; copy it through.
5. **Silent out-of-scope expansion.** If the user asks to suppress a dark-capability finding, add the directory to the explicit out-of-scope list in RESOLVER.md; don't silently ignore.
6. **Re-evaluating scripted rules in Tier-2.** Scripts are authoritative for the 11 Tier-1 rules; trust the `pass` envelope.
7. **Suppressing the inapplicable envelope.** When a sub-artifact (e.g., `.resolver/evals.yml`) is missing, the affected Tier-1 rule emits `fail` — do not collapse downstream rules to silent skip.
8. **Embellishing scripts' `recommended_changes`.** Each rule's recipe constant is canonical guidance sourced from `resolver-best-practices.md`. Copy it through; do not paraphrase.

## Key Instructions

- Run Tier-1 first; the FAIL exclusion list above gates judgment evaluation.
- Present the 4 Tier-2 dimensions in a single locked-rubric call; per-dimension calls degrade agreement.
- Include `RESOLVER.md` verbatim in the Tier-2 prompt — never summarize.
- The dark-capability scan is gated to depth 1–2 — deeper scans overwhelm with transient build outputs.
- Run evals only when `--run-evals` is passed; eval execution is slow.
- Recovery: read-only outside the Repair Loop; edits revertable via `git diff` / `git checkout`.

## Handoff

**Receives:** Target directory (defaults to CWD); walks up to the nearest `RESOLVER.md` and audits that resolver. Optional `--run-evals` flag.

**Produces:** A unified findings table merging the 11 Tier-1 envelopes (script JSON), 4 Tier-2 judgment findings, and optional Tier-3 eval-execution results. Each row: tier, rule_id, location, severity, reasoning + `recommended_changes` excerpt. Optionally — per user confirmation in the Repair Loop — targeted edits to RESOLVER.md, AGENTS.md, or `.resolver/evals.yml`.

**Chainable to:** `/build:build-resolver --regenerate` (rebuild managed region); `/build:build-resolver --add-filing <type>` (add missing filing row).
