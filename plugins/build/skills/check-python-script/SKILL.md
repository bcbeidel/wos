---
name: check-python-script
description: >
  Audits a standalone Python 3 script against 25 deterministic checks
  (shebang, `__main__` guard, argparse shape, declared dependencies,
  ruff-backed AST lints, line count, secret patterns) plus nine
  judgment dimensions (output discipline, input validation, dependency
  posture, performance intent, naming, function design, module-scope
  discipline, literal intent, commenting intent) and a Tier-3
  cross-script collision check. Use when the user wants to "audit a
  python script", "check my python script", "review this script",
  "lint a python script", "is this script safe", "what's wrong with
  my script", or "why is my script failing". Not for general-purpose
  shell scripts — route to `/build:check-bash-script`.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path]"
user-invocable: true
references:
  - ../../_shared/references/python-script-best-practices.md
  - references/check-collision.md
  - references/check-commenting-intent.md
  - references/check-dependency-posture.md
  - references/check-function-design.md
  - references/check-input-validation.md
  - references/check-literal-intent.md
  - references/check-module-scope-discipline.md
  - references/check-naming.md
  - references/check-output-discipline.md
  - references/check-performance-intent.md
license: MIT
---

# Check Python Script

Audit a standalone Python 3 script for structural soundness, dependency posture, ruff-backed lint cleanliness, and adherence to the project's Python conventions. The rubric — what makes a Python script load-bearing, the anatomy template, the patterns that work — lives in [python-script-best-practices.md](../../_shared/references/python-script-best-practices.md).

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 6 scripts emitting JSON envelopes via `_common.py` (25 rule_ids total, including 13 from `check_ruff.sh` wrapping ruff). Tier-2 has 9 judgment dimensions read inline by the primary agent. Tier-3 is `collision` (cross-script duplication).

## Workflow

### 1. Scope

Read `$ARGUMENTS`. Resolve to a `.py` file or directory walking top-level for Python scripts. Confirm scope aloud.

### 2. Tier-1 Deterministic Checks

Invoke 6 detection scripts:

```bash
SCRIPTS="${SKILL_DIR}/scripts"
TARGETS="$ARGUMENTS"

bash "$SCRIPTS/check_secrets.sh"   $TARGETS   # 1 rule:  secret (FAIL)
bash "$SCRIPTS/check_structure.sh" $TARGETS   # 6 rules: shebang, guard-missing, guard-shape, syntax (FAIL); main-returns, keyboard-interrupt (WARN)
bash "$SCRIPTS/check_argparse.sh"  $TARGETS   # 3 rules: argparse-when-argv, add-argument-help, subprocess-check (WARN)
bash "$SCRIPTS/check_deps.sh"      $TARGETS   # 1 rule:  declared-deps (WARN)
bash "$SCRIPTS/check_ruff.sh"      $TARGETS   # 13 rules wrapping ruff codes; inapplicable when ruff missing
bash "$SCRIPTS/check_size.sh"      $TARGETS   # 1 rule:  size (WARN)
```

Each script emits a JSON array of envelopes. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (25 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_secrets.sh` | `secret` | fail |
| `check_structure.sh` | `shebang`, `guard-missing`, `guard-shape`, `syntax` | fail |
| `check_structure.sh` | `main-returns`, `keyboard-interrupt` | warn |
| `check_argparse.sh` | `argparse-when-argv`, `add-argument-help`, `subprocess-check` | warn |
| `check_deps.sh` | `declared-deps` | warn |
| `check_ruff.sh` | `ruff-D100`, `ruff-SIM115`, `ruff-PLW1514`, `ruff-PTH`, `ruff-F401`, `ruff-ANN`, `ruff-format`, `ruff-fstring-modernize` | warn |
| `check_ruff.sh` | `ruff-E722`, `ruff-shell-true`, `ruff-S307`, `ruff-F403`, `ruff-S108` | fail |
| `check_size.sh` | `size` | warn |

The previously-INFO `exec-bit` rule is dropped (the pattern has no INFO; the executable-bit check still runs in `_ast_checks.py` for parity but emits no finding).

`ruff-S602` and `ruff-S604` consolidate into single rule_id `ruff-shell-true` (both about `shell=True` in subprocess). `ruff-UP031` and `ruff-UP032` consolidate into `ruff-fstring-modernize` (both about printf-style → f-string).

**Tier-2 exclusion list.** Any FAIL in `secret`, `shebang`, `guard-missing`, `guard-shape`, `syntax`, `ruff-E722`, `ruff-shell-true`, `ruff-S307`, `ruff-F403`, or `ruff-S108` excludes the script from Tier-2.

**Missing-tool degradation.** `check_ruff.sh` emits all 13 envelopes with `overall_status: inapplicable` and exits 0 when `ruff` is absent. Other scripts continue.

### 3. Tier-2 Judgment Dimensions

For each script that passed the Tier-2 exclusion gate, evaluate against the **9 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-output-discipline.md](references/check-output-discipline.md) | D1 — data to stdout, chatter to stderr | warn |
| [check-input-validation.md](references/check-input-validation.md) | D2 — argparse types narrow input early | warn |
| [check-dependency-posture.md](references/check-dependency-posture.md) | D3 — stdlib first; declared deps for the rest | warn |
| [check-performance-intent.md](references/check-performance-intent.md) | D4 — generators / context managers / file streaming | warn |
| [check-naming.md](references/check-naming.md) | D5 — snake_case, intent-naming | warn |
| [check-function-design.md](references/check-function-design.md) | D6 — small functions; main() orchestrator | warn |
| [check-module-scope-discipline.md](references/check-module-scope-discipline.md) | D7 — import + constant + main; no top-level work | warn |
| [check-literal-intent.md](references/check-literal-intent.md) | D8 — magic numbers / strings named via constants | warn |
| [check-commenting-intent.md](references/check-commenting-intent.md) | D9 — docstring + why-comments, no what-comments | warn |

#### Evaluator policy

- **Single locked-rubric pass per script.** Read all 9 rule files first, then evaluate the script in one LLM call.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`.
- **Severity floor: WARN.**
- **One finding per dimension maximum.**

### 4. Tier-3 Cross-Script Collision

Evaluate against [check-collision.md](references/check-collision.md). Surface duplicate logic across scripts (e.g., copy-pasted helper functions, duplicated argparse setups) as `warn`. Single-script scope returns `inapplicable`.

### 5. Report

Merge findings from all 3 tiers. Sort `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3. Each `Recommendation:` line copies through `recommended_changes` verbatim.

### 6. Opt-In Repair Loop

Ask once: "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:
- **Direct edit** — shebang, `__main__` guard, argparse help text, `pathlib.Path` over `os.path`, etc. Show diff; write on confirmation.
- **Routed to another skill** — substantial rewrites → `/build:build-python-script`.
- **Tier-2/3 judgment** — ask the user; rewrite the section; show diff.

After each fix, re-run the relevant Tier-1 script.

## Anti-Pattern Guards

1. **Per-dimension LLM call.** Collapse into one locked-rubric call per script.
2. **LLM-evaluating format compliance.** Shebang, guard, argparse shape — handle deterministically.
3. **Ambiguous compliance reported as PASS.** Surface as WARN.
4. **Bulk-applying fixes.** Per-finding confirmation required.
5. **Re-evaluating scripted rules in Tier-2.** Trust the `pass` envelope.
6. **Suppressing the inapplicable envelope.** When ruff is absent, the 13 ruff envelopes emit `inapplicable` — surface them.
7. **Embellishing scripts' `recommended_changes`.** Copy through; do not paraphrase.

## Key Instructions

- Run Tier-1 first; gate LLM evaluation on structural validity.
- `check_ruff.sh` consolidates 15 ruff codes into 13 rule_ids (`ruff-shell-true` covers S602+S604; `ruff-fstring-modernize` covers UP031+UP032).
- Recovery: read-only outside the Repair Loop.

## Handoff

**Receives:** Path to a `.py` file or directory containing Python scripts.

**Produces:** A unified findings table merging the 25 Tier-1 envelopes (script JSON), 9 Tier-2 judgment findings per script, and Tier-3 cross-script collision findings (multi-script scope only). Each row: tier, rule_id, location, status, reasoning + `recommended_changes` excerpt.

**Chainable to:** `/build:build-python-script` (rebuild non-compliant scripts from scratch).
