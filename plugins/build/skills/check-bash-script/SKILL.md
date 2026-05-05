---
name: check-bash-script
description: >
  Audits a Bash 4.0+ script against 34 deterministic rules emitted as
  JSON envelopes (shebang, `set -euo pipefail`, header comment,
  main + sourceable guard, readonly constants, mktemp+trap pairing,
  shellcheck rule set SC2086 / SC2046 / SC2068 / SC2154 / SC2155 /
  SC2006 / SC2010 / SC2012 / SC2045 / SC2013 / SC2162 / SC2038 /
  SC2164 / SC2002 / SC2294, shfmt format compliance, eval / GNU-flag /
  `/tmp/` literal flagging, secret patterns, line count, naming
  conventions, command preflight) plus six judgment dimensions
  (output discipline, input validation, performance intent, function
  design, commenting intent, cross-entity collision). Use when the
  user wants to "audit a bash script", "check this bash script",
  "review my bash script", "lint a bash script", "is this bash script
  safe", "what's wrong with my shell script", or "run shellcheck on
  this". Not for POSIX `sh` portability — refused at scope. Not for
  Python scripts — route to `/build:check-python-script`.
argument-hint: "[path]"
user-invocable: true
references:
  - ../../_shared/references/bash-script-best-practices.md
  - references/check-commenting-intent.md
  - references/check-cross-entity-collision.md
  - references/check-function-design.md
  - references/check-input-validation.md
  - references/check-output-discipline.md
  - references/check-performance-intent.md
license: MIT
---

# Check Bash Script

Audit a Bash 4.0+ script for structural soundness, safety, idiom
discipline, and adherence to the project's Bash conventions. The
rubric — what makes a script load-bearing, the anatomy template, the
patterns that work — lives in
[bash-script-best-practices.md](../../_shared/references/bash-script-best-practices.md).
This skill is the audit workflow; the principles doc is what it
audits against.

The audit runs in three tiers. **Tier-1** is deterministic — nine
detection scripts run per target and emit JSON envelopes, leaning hard
on `shellcheck` and `shfmt` for the heavy lifting. Each envelope is
self-sufficient: `{rule_id, overall_status, findings[]}` where every
finding includes a non-empty `recommended_changes` recipe. **Tier-2**
is judgment — read each `references/check-*.md` file (six surviving
LLM-judged dimensions) and evaluate the artifact against it directly;
produce one finding per dimension at most, default-closed when
borderline. **Tier-3** is cross-entity collision detection — when the
scope holds multiple scripts in the same directory, check for
duplicated logic the maintainer could consolidate.

Read-only by default. The opt-in repair loop applies fixes only after
per-finding confirmation. Each script's `recommended_changes` field is
the canonical repair guidance — no enrichment needed.

## Workflow

1. Scope → 2. Tier-1 Deterministic Checks → 3. Tier-2 Judgment
Checks → 4. Tier-3 Cross-Entity Collision → 5. Report → 6. Opt-In
Repair Loop.

### 1. Scope

Read `$ARGUMENTS`:

- **Single path to a `.sh` file (or extensionless executable)** —
  audit that file.
- **Directory path** — walk the directory, audit every `.sh` at the
  top level and every extensionless file with a bash shebang. Do not
  recurse into subdirectories — Bash scripts are top-level by
  convention, and recursion pulls in helpers / libraries / vendored
  shell that the audit does not model.
- **Empty** — refuse and explain: this skill operates on a target,
  not a configuration.

Confirm the scope aloud before proceeding (one line: "Auditing
<path> (N scripts found)").

### 2. Tier-1 Deterministic Checks

Run nine detection scripts in sequence against each target. Each emits
a JSON envelope (single-rule scripts) or a JSON array of envelopes
(multi-rule scripts) to stdout. Each exits `0` on clean / warn /
inapplicable, `1` on any `overall_status: fail`, `64` on argument
error, `69` on missing required dependency. Do not stop on any
script's exit `1` — all nine contribute findings to the merged report.

```bash
SCRIPTS="${SKILL_DIR}/scripts"   # resolved by Claude at invocation
TARGETS="$ARGUMENTS"

python3 "$SCRIPTS/check_secrets.py"        $TARGETS   # 1 rule:  secret (FAIL — excludes from Tier-2)
python3 "$SCRIPTS/check_structure.py"      $TARGETS   # 7 rules: shebang/strict-mode (FAIL); header/main/main-guard/readonly/mktemp-trap (WARN)
python3 "$SCRIPTS/check_idioms.py"         $TARGETS   # 3 rules: bracket-test, printf-over-echo, var-braces (WARN)
python3 "$SCRIPTS/check_safety.py"         $TARGETS   # 3 rules: eval, tmp-literal (FAIL); gnu-flags (WARN)
python3 "$SCRIPTS/check_shellcheck.py"     $TARGETS   # 15 rules wrapping shellcheck SC codes; inapplicable if shellcheck absent
python3 "$SCRIPTS/check_naming.py"         $TARGETS   # 1 rule:  naming (WARN — case, shadowing, weak names)
python3 "$SCRIPTS/check_preflight.py"      $TARGETS   # 1 rule:  preflight (WARN — external commands missing command -v)
bash    "$SCRIPTS/check_shfmt.sh"          $TARGETS   # 1 rule:  format (WARN); inapplicable if shfmt absent
bash    "$SCRIPTS/check_size.sh"           $TARGETS   # 2 rules: size, line-length (WARN)
```

The scripts live next to `SKILL.md` under `scripts/` and are executable.
Claude resolves `${SKILL_DIR}` from the skill's own directory at
invocation time — hooks use `$CLAUDE_PLUGIN_ROOT`, but skills do not.

**JSON envelope shape** — every script emits this (single envelope or
array of envelopes; documented in `assets/output-example.json`):

```json
{
  "rule_id": "shebang",
  "overall_status": "pass | warn | fail | inapplicable",
  "findings": [
    {
      "status": "warn | fail",
      "location": {"line": 1, "context": "<excerpt>"},
      "reasoning": "<≤2 sentences>",
      "recommended_changes": "<canonical repair recipe>"
    }
  ]
}
```

`recommended_changes` is **required** on every finding. Scripts embed
their own canonical repair recipes — no LLM enrichment needed.

**Single-artifact-per-rule discipline.** Every rule lives as exactly
one artifact: a script (when ≥70% mechanically detectable) **or** a
markdown file under `references/check-*.md` (when judgment-driven), but
never both. Tier-1 scripts cover 34 rules (the deterministic set);
`references/check-*.md` covers the 6 judgment dimensions.

**Script-to-rules map** (rule_ids each script emits):

| Script | rule_ids emitted |
|---|---|
| `check_secrets.py` | `secret` |
| `check_structure.py` | `shebang`, `strict-mode`, `header-comment`, `main-fn`, `main-guard`, `readonly-config`, `mktemp-trap-pairing` |
| `check_idioms.py` | `bracket-test`, `printf-over-echo`, `var-braces` |
| `check_safety.py` | `eval`, `gnu-flags`, `tmp-literal` |
| `check_shellcheck.py` | `unquoted-variable-expansion`, `unquoted-command-substitution`, `unquoted-args-expansion`, `eval-of-array`, `ls-grep-parsing`, `ls-instead-of-find`, `iterating-ls-output`, `referenced-but-not-assigned`, `unscoped-function-variable`, `backtick-command-substitution`, `for-line-in-cat`, `read-without-r`, `find-xargs-without-print0`, `cd-without-exit-handling`, `useless-cat` |
| `check_naming.py` | `naming` (~70% coverage; gaps documented in script docstring) |
| `check_preflight.py` | `preflight` (~75% coverage; gaps documented in script docstring) |
| `check_shfmt.sh` | `format` |
| `check_size.sh` | `size`, `line-length` |

**FAIL findings that exclude the file from Tier-2** (evaluation is not
useful until these are resolved):

- Any `secret` finding from `check_secrets.py`
- `shebang` FAIL from `check_structure.py` (`#!/bin/sh` or other
  non-bash — the file is not in scope)
- `eval` or `tmp-literal` FAIL from `check_safety.py`
- Any FAIL from `check_shellcheck.py` for `unquoted-variable-expansion`,
  `unquoted-command-substitution`, `unquoted-args-expansion`,
  `eval-of-array`, or the `ls-*` parse family — correctness bugs that
  bias every judgment dimension toward false negatives

**FAIL findings that do NOT exclude from Tier-2:** `strict-mode` FAIL
leaves a parseable bash script that judgment can still evaluate
productively.

**WARN / inapplicable findings never exclude.** They surface in the
report alongside Tier-2 findings.

### 3. Tier-2 Judgment Checks

For each file that passed the Tier-2-exclusion filter, read the six
surviving `references/check-*.md` files and judge the artifact
against each. Six dimensions, run together as a single coherent
rubric pass — no trigger gating, no per-rule subagent dispatch. A
dimension that does not apply (e.g., D2 Input Validation on a script
with no destructive operations) returns `inapplicable` silently
(empty findings, no surfacing in the report).

The six dimensions:

| File | Dimension | What it judges |
|---|---|---|
| [check-output-discipline.md](references/check-output-discipline.md) | D1 Output Discipline | Data to stdout / chatter to stderr; `die` helper present and used; meaningful non-zero exit codes on every failure path |
| [check-input-validation.md](references/check-input-validation.md) | D2 Input Validation & Destructive-Op Safety | Inputs validated before destructive work; `${var:?}` for required, `${var:-}` for optional; `--dry-run` for deletes/overwrites; no secrets in argv; `--` before untrusted args |
| [check-performance-intent.md](references/check-performance-intent.md) | D4 Performance Intent | Bash builtins over forking in hot loops; parameter expansion over `basename`/`dirname`/`sed` for simple string ops |
| [check-function-design.md](references/check-function-design.md) | D5 Function Design | `main()` reads as orchestrator (sequence of named operations); function bodies short and single-purpose |
| [check-commenting-intent.md](references/check-commenting-intent.md) | D7 Commenting Intent | Header comment names purpose / usage / dependencies; inline comments explain *why*, not *what*; TODOs carry an owner or ticket |
| [check-cross-entity-collision.md](references/check-cross-entity-collision.md) | T3 Cross-Entity Collision | Fires only when the audit scope holds multiple files: shared `die`/`usage`/`preflight` helpers candidate for extraction |

(D3 Subprocess & Tool Hygiene and D6 Naming were dissolved into Tier-1
scripts — `check_preflight.py` and `check_naming.py` respectively. The
mechanical portion of those rules is now scripted; the judgment portion
folds into D5 Function Design and the canonical convention doc
[bash-script-best-practices.md](../../_shared/references/bash-script-best-practices.md).)

**Evaluator policy** (RULERS-aligned, Hong et al. 2026):

- **Single locked-rubric pass per artifact.** Read all six files first,
  then evaluate each in turn against the same artifact. Don't
  re-decompose into sub-checks; the unified rubric stabilizes severity.
- **Default-closed when borderline.** If evidence is ambiguous or an
  exception nearly fits, return `warn`, not `pass`. False-positive
  WARNs cost a glance; false-negative PASSes erode trust.
- **Severity floor: WARN.** Judgment-mode findings default to WARN —
  coaching, not blocking. Escalate to FAIL only for safety concerns
  that Tier-1 missed (e.g., a hand-rolled SQL-shaped string in shell).
- **One finding per dimension maximum.** If a dimension identifies
  multiple problematic locations, surface the highest-signal one with
  concrete detail (line numbers, what to extract). Bulk findings train
  the user to disregard the audit.

### 4. Tier-3 Cross-Entity Collision

When the scope holds multiple scripts (directory walk, step 1), check
for structural duplication the maintainer could consolidate:

- Two or more scripts sharing identical or near-identical `die` /
  `usage` / `preflight` helper functions (candidate for a shared
  `_helpers.sh` sourced by each script)
- Identical or near-identical `main` argument-parsing blocks across
  scripts (the same `case "$1" in -h|--help) usage; exit 0 ;; esac`
  pattern repeated)
- Repeated `command -v` preflight blocks for the same dependency set

Report collisions as INFO findings — they are maintainer guidance,
not failures. Single-script scope skips this tier.

### 5. Report

Parse each script's stdout as JSON (single envelope or array). Merge
all findings (Tier-1 from JSON envelopes; Tier-2 from your judgment
pass) into a unified table sorted by severity (`fail` > `warn` >
`inapplicable`), then by file path. Deduplicate exact-match findings
at merge time — `shellcheck` occasionally emits the same SC code at
multiple lines.

```
<SEVERITY>  <path> — <rule_id>: <one-line reasoning>
  Recommendation: <recommended_changes excerpt>
```

For Tier-1 findings, `recommended_changes` comes from the script's
embedded recipe constant (canonical, no enrichment). For Tier-2
findings, you author it inline grounded in the rule's body.

Summary line at top and bottom: `N fail, N warn across N scripts`. If
any file was excluded from Tier-2, name it and the exclusion-trigger
finding.

### 6. Opt-In Repair Loop

After presenting findings, ask:

> "Apply fixes? Enter `y` (all), `n` (skip), or comma-separated
> finding numbers."

For each selected finding:

1. Read the finding's `recommended_changes` field — that is the
   canonical recipe for the fix.
2. Read the relevant section of the target file.
3. Propose a minimal specific edit — fix the finding without
   restructuring surrounding code.
4. Show the diff.
5. Write the change only on explicit user confirmation.
6. Re-run the Tier-1 script that produced the finding (or re-judge
   the Tier-2 dimension); confirm it now passes.

Per-change confirmation is non-negotiable. Bulk application removes
the user's ability to review individual edits.

## Anti-Pattern Guards

1. **Running Tier-2 before Tier-1** — deterministic checks are cheap
   and authoritative; running them first avoids spending judgment on
   files that should have been excluded.
2. **Trigger-gating Tier-2 dimensions** — all six dimensions run on
   every file. A dimension that doesn't apply returns `inapplicable`
   silently. Conditional dimensions produce inconsistent rubrics
   across runs and make findings non-comparable.
3. **Re-evaluating scripted rules in Tier-2** — scripts are
   authoritative for the 34 rules they cover. Don't second-guess a
   `pass` envelope by reading the artifact again for that rule;
   trust the script. The judgment pass is for the six dimensions
   that have NO script.
4. **Applying all repair fixes in one batch** — per-finding
   confirmation is required.
5. **Auditing recursively into subdirectories** — Bash scripts are
   top-level by convention; recursion pulls in libraries the rubric
   does not model. Top-level only.
6. **Skipping the re-run after a fix** — the repair loop's final step
   re-runs the script (or re-judges the dimension). A fix that
   produces a new finding elsewhere is more common than it sounds.
7. **Suppressing the inapplicable envelope** — when `shellcheck` or
   `shfmt` is absent, the `overall_status: inapplicable` envelope is
   the user's signal that coverage is reduced. Surfacing it is the
   contract; hiding it silently under-audits.
8. **Embellishing scripts' `recommended_changes`** — each script
   embeds the canonical repair recipe sourced from the deleted
   `rule-*.md` body content. Don't paraphrase or expand; copy through.

## Key Instructions

- Tier-1 scripts run first and always. Tier-2 runs only on files
  that passed the Tier-2-exclusion filter.
- All six Tier-2 dimensions are evaluated on every non-excluded
  file. A dimension that does not apply returns `inapplicable`
  silently.
- Parse Tier-1 stdout as JSON. Each script emits either a single
  envelope (`{rule_id, overall_status, findings}`) or a JSON array
  of envelopes (multi-rule scripts). The `recommended_changes` field
  on each finding is canonical — copy it through to the report.
- Repairs require per-finding confirmation — each change writes
  individually and waits for explicit approval before the next.
- When a Tier-1 script reports missing required dependencies (exit
  69), surface the dependency name and install hint.
- When `shellcheck` or `shfmt` is absent, the wrapper emits an
  envelope with `overall_status: inapplicable` and exits 0. Other
  scripts continue.
- Won't modify files without per-change confirmation — the audit is
  read-only by default; repair fixes opt in one at a time.
- Won't audit paths outside `$ARGUMENTS` — the scope the user named
  is the only scope.
- Won't audit POSIX `sh` scripts — out of scope; the principles doc
  this skill enforces is bash-only. The `shebang` FAIL from
  `check_structure.py` is the structural refusal.
- Recovery if a repair edit produces a worse state: the edit is a
  single file change; revert with `git checkout -- <path>` or the
  editor's undo.

## Handoff

**Receives:** Path to a single `.sh` file (or extensionless
executable with a bash shebang) or a directory holding such files at
the top level.
**Produces:** Structured findings table merging Tier-1 JSON envelopes
and Tier-2 judgment findings (`<SEVERITY>  <path> — <rule_id>:
<reasoning>` with a `Recommendation:` follow-up line drawn from the
finding's `recommended_changes`); optionally, targeted edits applied
after per-finding confirmation.
**Chainable to:** `/build:build-bash-script` (rebuild from scratch
after flagged repairs if the repair loop surfaces structural issues
bigger than point fixes).
