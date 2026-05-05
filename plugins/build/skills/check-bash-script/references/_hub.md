---
name: check-bash-script Rules — Hub
description: Index of all 40 rules check-bash-script enforces. Cross-rule framing notes (tiering, RULERS guidance, default-closed evaluator policy) live here, not in any single rule file.
---

# check-bash-script Rules

Per-rule files in this directory document the bash-script conventions
this skill enforces. Each rule's body follows the unified Claude-rule
shape from
[`rule-best-practices.md`](../../../_shared/references/rule-best-practices.md):
imperative + Why + How to apply + optional example + optional Exception.

The same rule body serves two consumers: Claude reads rules ambiently
when editing matching files (via `paths:` glob); the audit dispatcher
subagent reads them on-demand when scoring an artifact.

## Cross-rule framing

**Tier-1 fail findings short-circuit Tier-2.** Any `secret`, `shebang`
(non-bash), `eval`, `tmp-literal`, `unquoted-variable-expansion`,
`unquoted-command-substitution`, `unquoted-args-expansion`, or
`eval-of-array` finding excludes the file from Tier-2 evaluation.
Other FAILs (e.g., `strict-mode` missing) leave a parseable bash
script that judgment can still evaluate productively.

**Tier-2 evaluation: present all dimensions in one call.** RULERS
(Hong et al. 2026) advocates locked unified rubrics over decomposition
for stability and evidence-anchored scoring. Default-closed evaluator
policy: when evidence is borderline, surface as WARN, not PASS.
Severity defaults to WARN; judgment-level coaching, not blocking. A
dimension may escalate to FAIL when surfacing a safety concern Tier-1
missed (e.g., a hand-rolled SQL-shaped string in shell), but the
default is WARN — Tier-1 is where blocking lives.

**Missing-tool degradation.** `check_shellcheck.py` and
`check_shfmt.sh` emit an INFO finding (`tool-missing`) and exit 0 when
the wrapped tool is absent. The remaining scripts continue running.
The Missing Tools INFO is the user's signal that Tier-1 coverage is
reduced — surfacing it is the contract.

**One finding per Tier-2 dimension maximum.** If a dimension identifies
multiple problematic locations, surface the highest-signal one with
concrete detail (line numbers, what to extract). Bulk findings train
the user to disregard the audit.

**Cross-entity rules apply only across multiple files.** The Tier-3
`cross-entity-collision` rule fires when the audit scope holds two or
more scripts in the same directory. Single-file audits return
INAPPLICABLE for Tier-3.

## Deterministic Checks (32)

Each rule below has a script implementation in `../scripts/`. The
script detects violations; the rule body documents the convention for
both Claude (ambient editing) and the audit subagent (recipe
generation when a finding fires).

- [secret](rule-secret.md) — externalize API keys, tokens, private URLs to env vars
- [shebang](rule-shebang.md) — first line `#!/usr/bin/env bash`
- [strict-mode](rule-strict-mode.md) — `set -euo pipefail` in prologue
- [header-comment](rule-header-comment.md) — purpose / usage / dependencies / exit codes block
- [main-fn](rule-main-fn.md) — wrap top-level execution in `main`
- [main-guard](rule-main-guard.md) — sourceable guard at file bottom
- [readonly-config](rule-readonly-config.md) — top-level constants declared `readonly`
- [mktemp-trap-pairing](rule-mktemp-trap-pairing.md) — register `trap` immediately after `mktemp`
- [bracket-test](rule-bracket-test.md) — use `[[ ... ]]` not `[ ... ]`
- [printf-over-echo](rule-printf-over-echo.md) — `printf` for non-trivial output
- [var-braces](rule-var-braces.md) — brace expansions adjacent to identifier characters
- [eval](rule-eval.md) — avoid `eval` (use `case`, dispatch arrays)
- [gnu-flags](rule-gnu-flags.md) — declare GNU-coreutils dependency or use portable form
- [tmp-literal](rule-tmp-literal.md) — `mktemp` instead of hardcoded `/tmp/` paths
- [unquoted-variable-expansion](rule-unquoted-variable-expansion.md) — quote variable expansions (SC2086)
- [unquoted-command-substitution](rule-unquoted-command-substitution.md) — quote `$(...)` (SC2046)
- [unquoted-args-expansion](rule-unquoted-args-expansion.md) — use `"$@"` not `$@` (SC2068)
- [referenced-but-not-assigned](rule-referenced-but-not-assigned.md) — assign or guard variables (SC2154)
- [unscoped-function-variable](rule-unscoped-function-variable.md) — split `local var; var=...` (SC2155)
- [backtick-command-substitution](rule-backtick-command-substitution.md) — use `$(...)` not backticks (SC2006)
- [ls-grep-parsing](rule-ls-grep-parsing.md) — use globs instead of `ls | grep` (SC2010)
- [ls-instead-of-find](rule-ls-instead-of-find.md) — use `find` not `ls -l` parsing (SC2012)
- [iterating-ls-output](rule-iterating-ls-output.md) — iterate with globs not `$(ls)` (SC2045)
- [for-line-in-cat](rule-for-line-in-cat.md) — use `while IFS= read -r` not `for line in $(cat)` (SC2013)
- [read-without-r](rule-read-without-r.md) — `read -r` for verbatim input (SC2162)
- [find-xargs-without-print0](rule-find-xargs-without-print0.md) — `-print0` / `-0` pair (SC2038)
- [cd-without-exit-handling](rule-cd-without-exit-handling.md) — `cd "$d" || exit` (SC2164)
- [useless-cat](rule-useless-cat.md) — pipe directly from file (SC2002)
- [eval-of-array](rule-eval-of-array.md) — `"${cmd[@]}"` not `eval "${cmd[@]}"` (SC2294)
- [format](rule-format.md) — apply `shfmt -i 2 -ci -bn` canonical layout
- [size](rule-size.md) — keep scripts under 300 non-blank lines
- [line-length](rule-line-length.md) — keep lines under 100 characters

## Judgment Dimensions (7)

LLM-judged rules. The dispatcher subagent reads each rule body as the
rubric (judgment-mode evaluation against the artifact) and produces
structured `{rule_id, status, reasoning, recommended_changes}` output.

- [output-discipline](rule-output-discipline.md) — D1: stdout for data, stderr for chatter, exit-code contract
- [input-validation](rule-input-validation.md) — D2: validate early, dry-run flags, externalize secrets, `--` separator
- [subprocess-tool-hygiene](rule-subprocess-tool-hygiene.md) — D3: preflight commands, register cleanup traps, declare GNU deps
- [performance-intent](rule-performance-intent.md) — D4: builtins over external commands in loops
- [function-design](rule-function-design.md) — D5: orchestrator-style `main`, named helpers, sourceable guard
- [naming](rule-naming.md) — D6: snake_case locals, UPPERCASE constants, intent-naming, no shadowing
- [commenting-intent](rule-commenting-intent.md) — D7: header block, *why*-comments, tagged TODOs

## Cross-Entity (1)

Cross-script rules fire when the audit scope holds multiple scripts.

- [cross-entity-collision](rule-cross-entity-collision.md) — extract duplicated helpers across scripts in same directory
