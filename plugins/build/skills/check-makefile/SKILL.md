---
name: check-makefile
description: >
  Audits a top-level Makefile against 29 deterministic checks
  (strict-shell pin, `.SHELLFLAGS`, `MAKEFLAGS` warnings, `.PHONY`
  coverage, tab-indent, header comment, help-target patterns,
  variable-assignment discipline, top-level shell, destructive-op
  guards including `rm -rf`/`sudo`/global-install/curl-pipe, recipe
  hygiene, secrets, file/line size, optional `checkmake` wrap) plus
  seven judgment dimensions and a Tier-3 cross-Makefile collision
  check. Use when the user wants to "audit a makefile", "check my
  makefile", "review this makefile", "lint a makefile", "is my
  makefile any good", or "what's wrong with my makefile". Not for
  POSIX-`make`, compilation trees, or recursive multi-module builds —
  different rubric.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path]"
user-invocable: true
references:
  - ../../_shared/references/makefile-best-practices.md
  - references/check-collision.md
  - references/check-destructive-op-safety.md
  - references/check-documentation-intent.md
  - references/check-incremental-correctness.md
  - references/check-naming-and-structure.md
  - references/check-recipe-hygiene.md
  - references/check-target-contract-integrity.md
  - references/check-variable-and-override-discipline.md
license: MIT
---

# Check Makefile

Audit a top-level Makefile for structural soundness, safety, help/`.PHONY` coverage, recipe hygiene, and adherence to the workflow-orchestration rubric. The rubric — what makes a Makefile load-bearing, the anatomy template, the patterns that work — lives in [makefile-best-practices.md](../../_shared/references/makefile-best-practices.md).

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 11 scripts emitting JSON envelopes via `_common.py` (29 rule_ids total). Tier-2 has 7 judgment dimensions read inline by the primary agent. Tier-3 is `collision` (cross-Makefile drift in multi-Makefile scope).

## Workflow

### 1. Scope

Read `$ARGUMENTS`:

- **Single path to a `Makefile` (or `*.mk` file)** — audit that file.
- **Directory path** — walk the top level for `Makefile`, `GNUmakefile`, `*.mk`. Do not recurse — recursive multi-module builds are out of scope.
- **Empty** — refuse and explain.

Confirm scope aloud.

### 2. Tier-1 Deterministic Checks

Invoke 11 detection scripts:

```bash
SCRIPTS="${SKILL_DIR}/scripts"
TARGETS="$ARGUMENTS"

python3 "$SCRIPTS/check_secrets.py"   $TARGETS   # 1 rule:  secret (FAIL)
python3 "$SCRIPTS/check_structure.py" $TARGETS   # 7 rules: shell-pin, shellflags (FAIL); warn-undefined, no-builtin-rules, delete-on-error, default-goal, header-comment (WARN)
python3 "$SCRIPTS/check_phony.py"     $TARGETS   # 1 rule:  phony-coverage (WARN)
python3 "$SCRIPTS/check_help.py"      $TARGETS   # 3 rules: help-target, help-auto, help-desc (WARN)
python3 "$SCRIPTS/check_indent.py"    $TARGETS   # 1 rule:  tab-indent (FAIL)
python3 "$SCRIPTS/check_naming.py"    $TARGETS   # 2 rules: target-name, helper-prefix (WARN)
python3 "$SCRIPTS/check_variables.py" $TARGETS   # 2 rules: assignment-op, top-level-shell (WARN)
python3 "$SCRIPTS/check_safety.py"    $TARGETS   # 5 rules: unguarded-rm, sudo, global-install, curl-pipe (FAIL); destructive-guard (WARN)
python3 "$SCRIPTS/check_recipes.py"   $TARGETS   # 4 rules: literal-make, at-discipline, or-true-guard, recipe-length (WARN)
bash    "$SCRIPTS/check_checkmake.sh" $TARGETS   # 1 rule:  checkmake (WARN); inapplicable when absent
bash    "$SCRIPTS/check_size.sh"      $TARGETS   # 2 rules: size, line-length (WARN)
```

Each script emits a JSON array of envelopes. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (29 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_secrets.py` | `secret` | fail |
| `check_structure.py` | `shell-pin`, `shellflags` | fail |
| `check_structure.py` | `warn-undefined`, `no-builtin-rules`, `delete-on-error`, `default-goal`, `header-comment` | warn |
| `check_phony.py` | `phony-coverage` | warn |
| `check_help.py` | `help-target`, `help-auto`, `help-desc` | warn |
| `check_indent.py` | `tab-indent` | fail |
| `check_naming.py` | `target-name`, `helper-prefix` | warn |
| `check_variables.py` | `assignment-op`, `top-level-shell` | warn |
| `check_safety.py` | `unguarded-rm`, `sudo`, `global-install`, `curl-pipe` | fail |
| `check_safety.py` | `destructive-guard` | warn |
| `check_recipes.py` | `literal-make`, `at-discipline`, `or-true-guard`, `recipe-length` | warn |
| `check_checkmake.sh` | `checkmake` | warn |
| `check_size.sh` | `size`, `line-length` | warn |

The previously-INFO `helper-prefix` rule is remapped to `warn` (the pattern has no INFO).

**Tier-2 exclusion list.** Any FAIL in `secret`, `shell-pin`, `shellflags`, `tab-indent`, `unguarded-rm`, `sudo`, `global-install`, or `curl-pipe` excludes the Makefile from Tier-2.

**Missing-tool degradation.** `check_checkmake.sh` emits an envelope with `overall_status: inapplicable` and exits 0 when `checkmake` is absent. Other scripts continue.

### 3. Tier-2 Judgment Dimensions

For each Makefile that passed the Tier-2 exclusion gate, evaluate against the **7 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-target-contract-integrity.md](references/check-target-contract-integrity.md) | D1 — public target surface fulfills the workflow-orchestration contract | warn |
| [check-destructive-op-safety.md](references/check-destructive-op-safety.md) | D2 — destructive ops are guarded, scoped, or reversible | warn |
| [check-recipe-hygiene.md](references/check-recipe-hygiene.md) | D3 — recipes use `$(MAKE)`, `@`-discipline, judicious `\|\| true` | warn |
| [check-variable-and-override-discipline.md](references/check-variable-and-override-discipline.md) | D4 — assignment ops reflect intent; no top-level shell | warn |
| [check-incremental-correctness.md](references/check-incremental-correctness.md) | D5 — file targets list real prerequisites; `.PHONY` annotated | warn |
| [check-naming-and-structure.md](references/check-naming-and-structure.md) | D6 — target names verb-ish; helpers prefixed; sections grouped | warn |
| [check-documentation-intent.md](references/check-documentation-intent.md) | D7 — header comment + per-target `## help`; comments explain why | warn |

#### Evaluator policy

- **Single locked-rubric pass per Makefile.** Read all 7 rule files first, then evaluate the Makefile in one LLM call.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`.
- **Severity floor: WARN.**
- **One finding per dimension maximum.**

### 4. Tier-3 Cross-Makefile Collision

Evaluate against [check-collision.md](references/check-collision.md). For multi-Makefile scope (`Makefile` + sibling `*.mk` files), surface duplicate `.PHONY` lists, divergent `SHELL` pins, or competing `help` definitions as `warn`. Single-Makefile scope returns `inapplicable`.

### 5. Report

Merge findings from all 3 tiers into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3 within severity. Each `Recommendation:` line copies through `recommended_changes` verbatim.

### 6. Opt-In Repair Loop

Ask once: "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:

- **Direct edit** — `SHELL` pin, `.SHELLFLAGS`, missing `.PHONY` entry, tab-indent fix, help-target awk parser. Show diff; write on confirmation.
- **Routed to another skill** — substantial rewrites → `/build:build-makefile`.
- **Tier-2/3 judgment** — ask the user; rewrite the section; show diff.

After each fix, re-run the relevant Tier-1 script.

## Anti-Pattern Guards

1. **Per-dimension LLM call.** Collapse into one locked-rubric call per Makefile.
2. **LLM-evaluating format compliance.** SHELL pin, `.PHONY` membership, tab-indent — handle deterministically in Tier-1.
3. **Ambiguous compliance reported as PASS.** Surface as WARN.
4. **Bulk-applying fixes.** Per-finding confirmation required.
5. **Re-evaluating scripted rules in Tier-2.** Trust the `pass` envelope.
6. **Suppressing the inapplicable envelope.** When `checkmake` is absent, the corresponding envelope emits `inapplicable` — surface it.
7. **Embellishing scripts' `recommended_changes`.** Copy through; do not paraphrase.
8. **Auditing recursively.** Top-level Makefiles + sibling `*.mk` only; recursive multi-module builds are out of scope.

## Key Instructions

- Run Tier-1 deterministic checks first; gate LLM evaluation on structural validity.
- The `check_checkmake.sh` wrapper gracefully degrades to `inapplicable` when `checkmake` is absent.
- Recovery: read-only outside the Repair Loop.

## Handoff

**Receives:** Path to a single `Makefile` / `GNUmakefile` / `*.mk` or a directory holding such files at the top level.

**Produces:** A unified findings table merging the 29 Tier-1 envelopes (script JSON), 7 Tier-2 judgment findings per Makefile, and Tier-3 cross-Makefile collision findings (multi-file scope only). Each row: tier, rule_id, location, status, reasoning + `recommended_changes` excerpt. Optionally — per user confirmation in the Repair Loop — targeted edits to Makefile.

**Chainable to:** `/build:build-makefile` (rebuild non-compliant Makefile from scratch).
