---
name: PILOT NOTES — check-bash-script Rule Decomposition
description: Working notes captured during the per-rule decomposition pilot — alignment audit, recompose sketches, script-binding inventory, observed surprises, and rollout recommendations.
---

# PILOT NOTES — check-bash-script Rule Decomposition

Companion to [`.plans/2026-05-04-check-bash-script-rule-decomposition.plan.md`](2026-05-04-check-bash-script-rule-decomposition.plan.md).

This file captures decisions and observations made during execution. Five sections:

- [Alignment audit](#alignment-audit) — Task 1 deliverable
- [Recompose sketches](#recompose-sketches) — Task 1 deliverable
- [Script-binding inventory](#script-binding-inventory) — Task 1 deliverable; input to follow-up #407
- [Recompose surprises](#recompose-surprises) — populated during Tasks 2–4
- [Rollout recommendations](#rollout-recommendations) — populated during Task 6
- [Cross-skill rule duplication observations](#cross-skill-rule-duplication-observations) — populated during Task 6

---

## Alignment audit

40 rules total: **32 Tier-1 deterministic + 7 Tier-2 judgment + 1 Tier-3 cross-entity.** Every rule has 1:1 alignment between `audit-dimensions.md` (definition) and `repair-playbook.md` (recipe). **Zero orphans.**

### Tier-1 — Deterministic Checks (32 after splits)

| Rule id | audit-dimensions.md | repair-playbook.md | Severity |
|---|---|---|---|
| `secret` | L24 | L47–L65 | FAIL |
| `shebang` | L25 | L71–L82 | FAIL |
| `strict-mode` | L26 | L84–L109 | FAIL |
| `header-comment` | L27 | L111–L142 | WARN |
| `main-fn` | L28 | L144–L171 | WARN |
| `main-guard` | L29 | L173–L192 | WARN |
| `readonly-config` | L30 | L194–L211 | WARN |
| `mktemp-trap-pairing` | L31 | L213–L233 | WARN |
| `bracket-test` | L32 | L239–L248 | WARN |
| `printf-over-echo` | L33 | L250–L259 | WARN |
| `var-braces` | L34 | L261–L270 | WARN |
| `eval` | L35 | L276–L294 | FAIL |
| `gnu-flags` | L36 | L296–L313 | WARN |
| `tmp-literal` | L37 | L315–L328 | FAIL |
| `unquoted-variable-expansion` (SC2086) | L38 | L337–L346 | FAIL |
| `unquoted-command-substitution` (SC2046) | L39 | L348–L356 | FAIL |
| `unquoted-args-expansion` (SC2068) | L40 | L358–L366 | FAIL |
| `referenced-but-not-assigned` (SC2154) | L41 | L368–L377 | WARN |
| `unscoped-function-variable` (SC2155) | L42 | L379–L393 | WARN |
| `backtick-command-substitution` (SC2006) | L43 | L395–L403 | WARN |
| `ls-grep-parsing` (SC2010 — split) | L44 | L405–L413 | FAIL |
| `ls-instead-of-find` (SC2012 — split) | L44 | L405–L413 | FAIL |
| `iterating-ls-output` (SC2045 — split) | L44 | L405–L413 | FAIL |
| `for-line-in-cat` (SC2013 — split) | L45 | L415–L429 | WARN |
| `read-without-r` (SC2162 — split) | L45 | L415–L429 | WARN |
| `find-xargs-without-print0` (SC2038) | L46 | L431–L441 | WARN |
| `cd-without-exit-handling` (SC2164) | L47 | L443–L453 | WARN |
| `useless-cat` (SC2002) | L48 | L455–L464 | WARN |
| `eval-of-array` (SC2294) | L49 | L466–L475 | FAIL |
| `format` | L50 | L481–L491 | WARN |
| `size` | L51 | L497–L511 | WARN |
| `line-length` | L52 | L513–L533 | WARN |

**Combined-entry splits.** Two source rows combine multiple SC codes; each becomes its own per-rule file:
- `SC2010 / SC2012 / SC2045` → 3 files. The combined recipe (parse `ls` output → use globs/`find -print0`) is the same; differentiation is per-rule context (SC2010 is `ls | grep`; SC2012 is `ls -l`; SC2045 is iterating `ls`).
- `SC2013 / SC2162` → 2 files. SC2013 is the `for line in $(cat file)` anti-pattern; SC2162 is the `-r` flag on `read`. Same recipe direction (`while IFS= read -r`); per-rule files clarify which lint code is being avoided.

### Tier-2 — Judgment Dimensions (7)

| Rule id | audit-dimensions.md | repair-playbook.md |
|---|---|---|
| `output-discipline` (D1) | L73–L89 | L543–L563 |
| `input-validation` (D2) | L91–L113 | L565–L592 |
| `subprocess-tool-hygiene` (D3) | L115–L135 | L594–L621 |
| `performance-intent` (D4) | L137–L153 | L623–L633 |
| `function-design` (D5) | L155–L172 | L635–L655 |
| `naming` (D6) | L174–L188 | L657–L667 |
| `commenting-intent` (D7) | L190–L205 | L669–L689 |

### Tier-3 — Cross-Entity (1)

| Rule id | audit-dimensions.md | repair-playbook.md |
|---|---|---|
| `cross-entity-collision` | L207–L217 | L693–L717 |

### Cross-rule framing (lives in `_hub.md`, not in any single rule)

Material in `audit-dimensions.md` that does NOT belong to any specific rule:
- L8–L12 — overview ("audit runs in three tiers")
- L14–L20 — Tier-1 framing (lint format, exit codes)
- L54–L64 — FAIL exclusions from Tier-2; missing-tool degradation
- L66–L71 — Tier-2 framing (one LLM call per file; all dimensions run; severity defaults)
- L219–L235 — Cross-Dimension Notes (all dimensions run; one finding max; severity)

Material in `repair-playbook.md` that does NOT belong to any specific rule:
- L13–L15 — HINT-severity note (feed-forward, not repair targets)
- L33–L42 — Format spec (Signal/CHANGE/FROM/TO/REASON)
- L721–L737 — Notes (per-finding confirmation; re-run; missing-tool not a repair target)

All of this lives in `_hub.md`.

---

## Recompose sketches

For each rule, a 2–3 line sketch of the unified Claude-rule body shape: (1) imperative; (2) Why; (3) How to apply. Full prose written during Tasks 2–4.

### Tier-1 sketches

**`rule-secret.md`**
- Imperative: Read API keys, tokens, and private URLs from environment variables, never embedded in source.
- Why: secrets in committed source leak through git history, logs, and backups; an exposed key requires rotation across every dependent system.
- How: replace literal with `"${VAR:?MESSAGE env var required}"` near the top of the script; use a secret manager where available.

**`rule-shebang.md`**
- Imperative: Begin every bash script with `#!/usr/bin/env bash` (or `#!/bin/bash` in tightly controlled environments).
- Why: `#!/bin/sh` invites silent bashisms-fail-on-dash bugs; missing shebang means the script runs under whatever shell the invoker happens to have.
- How: replace the first line; this skill is bash-only — non-bash shebangs are a routing error elsewhere.

**`rule-strict-mode.md`**
- Imperative: Enable strict-mode error handling with `set -euo pipefail` immediately after the shebang and header comment.
- Why: strict mode turns silent failures, unset-variable typos, and mid-pipeline errors into loud, early exits. Without it, `$user_imput` silently expands to empty.
- How: insert `set -euo pipefail` before any executable code; use `set -Eeuo pipefail` if also installing an ERR trap.

**`rule-header-comment.md`**
- Imperative: Include a header comment block in the first 10 lines naming purpose, usage, dependencies, and exit codes.
- Why: the header is the first thing a reader sees; a script without one is opaque to anyone who isn't the author.
- How: use the canonical block: name + one-line purpose, Usage line, Dependencies list, Exit codes list.

**`rule-main-fn.md`**
- Imperative: Wrap top-level execution logic in a `main` function.
- Why: a `main` function makes the script sourceable for testing and gives a single entry point a reader can find immediately.
- How: replace inline top-level statements with `main() { ... }` followed by `main "$@"`.

**`rule-main-guard.md`**
- Imperative: Gate `main "$@"` behind a sourceable guard at the bottom of the file.
- Why: the guard lets the file be sourced for testing (`. ./script.sh` loads functions without running `main`); without it, sourcing the file runs the entire script as a side effect.
- How: replace `main "$@"` with `[[ "${BASH_SOURCE[0]}" == "${0}" ]] && main "$@"` (or the `if`-block equivalent).

**`rule-readonly-config.md`**
- Imperative: Declare top-level configuration constants with `readonly`.
- Why: `readonly` makes accidental reassignment a hard error and signals to the reader that the value is configuration, not state.
- How: prefix `TIMEOUT=30` with `readonly`; restrict to non-trivial top-level constants (skip loop counters and similar ephemeral values).

**`rule-mktemp-trap-pairing.md`**
- Imperative: Register a cleanup `trap` immediately after `mktemp` (or before, when feasible).
- Why: without the trap, the temp directory leaks on any non-zero exit (including signals) — disk fills up; subsequent runs collide.
- How: capture `tmpdir="$(mktemp -d)"` then `trap 'rm -rf "$tmpdir"' EXIT INT TERM` immediately after.

**`rule-bracket-test.md`**
- Imperative: Use `[[ ... ]]` for test expressions in bash scripts.
- Why: `[[ ]]` does not word-split inside the brackets, supports pattern matching, and has saner numeric / string comparison; there's no portability cost in a bash-only file.
- How: replace `[ "$x" = "y" ]` with `[[ "$x" == "y" ]]`.

**`rule-printf-over-echo.md`**
- Imperative: Use `printf` for non-trivial output (escapes, format specifiers, or multi-arg).
- Why: `echo`'s handling of `-e`, `-n`, and escape sequences varies across shells; `printf` is portable and does what you wrote.
- How: replace `echo -e "...\t..."` with `printf '%s\t%s\n' "$a" "$b"`.

**`rule-var-braces.md`**
- Imperative: Brace variable expansions when adjacent to identifier characters.
- Why: `"$prefixfoo"` is a different (probably empty) variable; `"${prefix}foo"` is unambiguous.
- How: replace `"$var$other"` with `"${var}${other}"` when expansions are adjacent.

**`rule-eval.md`**
- Imperative: Avoid `eval`; use targeted constructs (parameter expansion, `case`, dispatch tables) instead.
- Why: `eval` on input is shell injection — full stop. Most `eval` uses are pattern matches that `case` or arrays cover safely.
- How: replace with `case "$action" in start) ... ;; esac`; if `eval` is genuinely required, justify with `# shellcheck disable=SC2294 # <reason>`.

**`rule-gnu-flags.md`**
- Imperative: Either declare GNU-coreutils dependency in the header comment, or replace GNU-specific flags with portable alternatives.
- Why: `sed -i` accepts no argument on GNU and requires a backup-suffix argument on macOS/BSD; silent cross-platform divergence is a recurring real-world failure.
- How: add `# Dependencies: gnu-coreutils` to header, or rewrite `sed -i 's/.../.../' file` as `sed '...' file > file.new && mv file.new file`.

**`rule-tmp-literal.md`**
- Imperative: Use `mktemp` plus a cleanup trap; avoid hardcoded `/tmp/` and `/var/tmp/` paths.
- Why: predictable temp paths invite races (other processes can guess the name) and symlink attacks (a malicious symlink at the expected location redirects writes elsewhere).
- How: replace `out="/tmp/work_$$"` with `out="$(mktemp)"; trap 'rm -f "$out"' EXIT INT TERM`.

**`rule-unquoted-variable-expansion.md` (SC2086)**
- Imperative: Quote variable expansions to prevent word-splitting and globbing.
- Why: without quotes, `$files` word-splits on `IFS` and globs filenames containing `*` / `?`; the single largest source of real-world bash bugs.
- How: replace `for f in $files` with `for f in "$files"` or `for f in "${files[@]}"` for arrays.

**`rule-unquoted-command-substitution.md` (SC2046)**
- Imperative: Quote command substitutions: `"$(cmd)"` not `$(cmd)`.
- Why: same word-splitting/globbing as SC2086, applied to substitution output.
- How: replace `cmd $(other_cmd)` with `cmd "$(other_cmd)"`.

**`rule-unquoted-args-expansion.md` (SC2068)**
- Imperative: Use `"$@"` (quoted) when passing positional arguments through.
- Why: `"$@"` preserves argument boundaries (whitespace, special characters); `$@` unquoted re-splits arguments and merges them.
- How: replace `cmd $@` with `cmd "$@"`.

**`rule-referenced-but-not-assigned.md` (SC2154)**
- Imperative: Either assign the variable, default it with `${var:-default}`, or guard it with `${var:?message}`.
- Why: shellcheck's static analysis caught a likely typo or forgotten assignment.
- How: replace bare `"$var"` with `"${var:?var required}"` to fail fast, or initialize before use.

**`rule-unscoped-function-variable.md` (SC2155)**
- Imperative: Split `local var=$(cmd)` into a `local` declaration plus an assignment so the exit status of `cmd` is preserved.
- Why: `local var=$(cmd)` masks `cmd`'s return code (because `local` itself returns 0), defeating `set -e`.
- How: replace with `local var; var="$(cmd)"`.

**`rule-backtick-command-substitution.md` (SC2006)**
- Imperative: Use `$(...)` for command substitution; avoid backticks.
- Why: `$(...)` is nestable, more readable, and universally supported by linters and modern shells; backticks are a 1980s relic.
- How: replace `\`cmd\`` with `$(cmd)`.

**`rule-ls-grep-parsing.md` (SC2010)**
- Imperative: Use globs or `find` instead of `ls | grep` to filter filenames.
- Why: filenames with spaces, newlines, or leading dashes break `ls`-based parsing.
- How: replace `ls | grep '\.log$'` with `*.log` glob or `find . -name '*.log'`.

**`rule-ls-instead-of-find.md` (SC2012)**
- Imperative: Use `find` instead of `ls -l` for programmatic file information.
- Why: `ls`'s output format is not stable and breaks on locale differences and unusual filenames.
- How: replace `ls -l` with `find . -maxdepth 1 -type f -printf '%s %p\n'`.

**`rule-iterating-ls-output.md` (SC2045)**
- Imperative: Iterate filenames with globs (`for f in *.ext`), not by parsing `ls` output.
- Why: filenames with spaces or special characters break `ls` parsing.
- How: replace `for f in $(ls *.log)` with `for f in *.log`; if no matches, guard with `shopt -s nullglob`.

**`rule-for-line-in-cat.md` (SC2013)**
- Imperative: Read file lines with `while IFS= read -r line; do ... done < file`, not `for line in $(cat file)`.
- Why: the `for in $(cat)` idiom word-splits on `IFS` and globs each line — it's wrong, not just slow.
- How: replace with the `while IFS= read -r` pattern.

**`rule-read-without-r.md` (SC2162)**
- Imperative: Use `read -r` to disable backslash-escape interpretation when reading lines.
- Why: without `-r`, `read` interprets `\` as an escape character, mangling input.
- How: replace `while read line` with `while IFS= read -r line`.

**`rule-find-xargs-without-print0.md` (SC2038)**
- Imperative: Pair `find ... -print0` with `xargs -0` (or use `find -exec ... {} +`) when piping filenames.
- Why: default whitespace separation in `xargs` breaks on filenames with spaces or newlines.
- How: replace `find ... | xargs cmd` with `find ... -print0 | xargs -0 cmd` or `find ... -exec cmd {} +`.

**`rule-cd-without-exit-handling.md` (SC2164)**
- Imperative: Guard `cd` calls with `|| exit` (or `|| return` inside a function), or rely on `set -e` and document that.
- Why: a failed `cd` followed by `rm -rf *` operates on the current directory — a destroyed-systems pattern.
- How: replace `cd /some/dir` with `cd /some/dir || exit`.

**`rule-useless-cat.md` (SC2002)**
- Imperative: Pipe directly from a file rather than `cat file | cmd`.
- Why: shellcheck flags this as wasteful (one extra fork). Some authors prefer the left-to-right `cat | cmd` reading order.
- How: replace `cat file | grep pattern` with `grep pattern file`. If the read-order is preferred, leave a `# shellcheck disable=SC2002` justification.

**`rule-eval-of-array.md` (SC2294)**
- Imperative: Pass array contents directly without `eval`.
- Why: `eval "${cmd[@]}"` performs a second shell-parsing pass over the expanded values, re-introducing injection vulnerability for any value containing shell metacharacters.
- How: replace `eval "${cmd[@]}"` with `"${cmd[@]}"`.

**`rule-format.md`**
- Imperative: Format bash scripts with `shfmt -i 2 -ci -bn` so the canonical layout (2-space indent, case-indent, binop on next line) is the source of truth.
- Why: formatter drift produces noisy diffs and triggers the "someone fix the spacing" PR trickle.
- How: run `shfmt -w -i 2 -ci -bn <file>` to apply.

**`rule-size.md`**
- Imperative: Keep scripts under 300 non-blank lines; extract or convert when larger.
- Why: bash's lack of data structures and error handling does not scale; past ~300 lines, a refactor is cheaper than maintenance.
- How: extract cohesive sections into helper scripts (`source`d), or convert to a real language.

**`rule-line-length.md`**
- Imperative: Keep lines under 100 characters.
- Why: long lines are unreadable in code review and break side-by-side diff views.
- How: break with `\` continuation, multi-line subshells, or extract a helper.

### Tier-2 sketches

**`rule-output-discipline.md` (D1)**
- Imperative: Route data output to stdout, logs/errors/prompts to stderr, and ensure every error branch exits non-zero.
- Why: Unix pipelines depend on the stdout-for-data / stderr-for-chatter convention; callers in cron, CI, and Makefiles depend on the exit-code contract.
- How: define a `die` helper for failure paths; use `>&2` for log/error output; ensure error branches end with `die` or `exit N` where `N > 0`.
- Rubric content: PASS conditions, common fail signals — drives the LLM's judgment.

**`rule-input-validation.md` (D2)**
- Imperative: Validate inputs early, gate destructive operations behind dry-run flags, and externalize secrets from argv.
- Why: "fail before damage" is cheap to implement and expensive to skip; `--dry-run` that isn't consulted is worse than no flag.
- How: use `${var:?message}` for required inputs; check `[[ -e "$path" ]]` before destructive ops; consult `--dry-run` in the destructive branch; use `--` before user-supplied arguments to commands like `rm`/`grep`/`mv`/`cp`.
- Rubric content: PASS conditions for required-input checks, dry-run wiring, secret externalization, `--` separator usage.

**`rule-subprocess-tool-hygiene.md` (D3)**
- Imperative: Preflight required external commands, register cleanup traps for created state, and declare or avoid GNU-specific flags.
- Why: failing fast with an actionable message ("missing: jq") beats failing mid-run with cryptic "command not found".
- How: define `preflight()` checking `command -v` for each external dep; register `trap 'cleanup' EXIT INT TERM` before `mktemp` or connection-open; document GNU-coreutils dependency in the header when GNU flags are used.
- Rubric content: PASS conditions for preflight, trap registration, GNU-flag handling.

**`rule-performance-intent.md` (D4)**
- Imperative: Replace external-command calls inside loops with bash builtins or parameter expansion when feasible.
- Why: each external invocation in a tight loop is a fork; parameter expansion is in-process and typically 100×+ faster.
- How: replace `basename "$f" .log` with `${f%.log}`; replace `cat file | grep pattern` with `grep pattern file`; eliminate unnecessary subshells.
- Rubric content: PASS conditions for builtin usage, common fail signals (per-iteration `date`/`wc`/`basename`).

**`rule-function-design.md` (D5)**
- Imperative: Make `main` an orchestrator of named helpers; keep helpers small and intent-named; provide a sourceable guard.
- Why: short named helpers read as their own commentary; the sourceable guard enables `bats` / `shunit2` testing.
- How: extract cohesive sections of long `main` into verb-phrased helpers; ensure each helper does one thing; gate `main "$@"` behind the BASH_SOURCE guard.
- Rubric content: PASS conditions for orchestrator structure, helper naming, guard presence.

**`rule-naming.md` (D6)**
- Imperative: Use `snake_case` for local variables, `UPPERCASE` for env vars and module-level constants, intent-naming throughout, and avoid shadowing builtins.
- Why: bash's lack of types makes naming the load-bearing documentation.
- How: rename `Tmp` → `raw_records`; rename `x` → `row_count`; avoid local variables named `echo`, `set`, `local`.
- Rubric content: PASS conditions for case conventions, intent-naming, no-shadowing.

**`rule-commenting-intent.md` (D7)**
- Imperative: Write a header comment naming purpose / usage / dependencies, and inline comments that explain *why* (not what).
- Why: comments that restate code rot alongside it; comments that explain *why* stay useful; untagged TODOs accumulate as orphan maintenance debt.
- How: header in first 10 lines covers purpose / usage / dependencies; inline comments explain rationale, constraints, workarounds; TODOs carry an owner or ticket.
- Rubric content: PASS conditions for header presence, inline-comment intent, TODO tagging.

### Tier-3 sketch

**`rule-cross-entity-collision.md`**
- Imperative: Extract duplicated helpers, argument parsing, and error handling shared across scripts in the same directory into a `_helpers.sh` (or similar) sourced by each.
- Why: shared utilities drift when maintained in triplicate; a single source of truth keeps the helpers coherent.
- How: identify the duplicated block; create `<dir>/_helpers.sh`; replace per-script copies with `source "$(dirname "${BASH_SOURCE[0]}")/_helpers.sh"`; if scripts are truly independent, accept the duplication.

---

## Script-binding inventory

Per-rule script function bindings. Used by follow-up [#407](https://github.com/bcbeidel/toolkit/issues/407) to formalize the script-binding audit dimension in `check-skill`.

**Important finding**: the binding is **NOT 1:1 by function name**. Some scripts have one function that emits findings for multiple rules (e.g., `check_idioms.py::_check_file` emits findings for `bracket-test`, `printf-over-echo`, `var-braces`). Issue #407 should not assume strict `check_<rule_id>` naming convention — the audit needs richer mapping data.

| Rule id | Script | Function | 1:1? |
|---|---|---|---|
| `secret` | `check_secrets.py` | `_scan_file` | N (per-file scan, not per-rule) |
| `shebang` | `check_structure.py` | `_check_shebang` | Y |
| `strict-mode` | `check_structure.py` | `_check_strict_mode` | Y |
| `header-comment` | `check_structure.py` | `_check_header_comment` | Y |
| `main-fn` | `check_structure.py` | `_check_main_fn` | Y |
| `main-guard` | `check_structure.py` | `_check_main_guard` | Y |
| `readonly-config` | `check_structure.py` | `_check_readonly_config` | Y |
| `mktemp-trap-pairing` | `check_structure.py` | `_check_mktemp_trap` | Y |
| `bracket-test` | `check_idioms.py` | `_check_file` | N (single fn, three rules) |
| `printf-over-echo` | `check_idioms.py` | `_check_file` | N |
| `var-braces` | `check_idioms.py` | `_check_file` | N |
| `eval` | `check_safety.py` | `_check_eval` | Y |
| `gnu-flags` | `check_safety.py` | `_check_gnu_flags` | Y |
| `tmp-literal` | `check_safety.py` | `_check_tmp_literal` | Y |
| All shellcheck rules (SC*) | `check_shellcheck.py` | `_check_file` | N (one fn delegates to `shellcheck` binary) |
| `format` | `check_shfmt.sh` | `check_one` | N (function name doesn't match rule id) |
| `size` | `check_size.sh` | `check_file` | N (one fn emits two rules) |
| `line-length` | `check_size.sh` | `check_file` | N |

**Implication for #407.** The audit should support multiple binding shapes:
- **Direct binding:** `script_function == "_check_<rule_id>"` (clean 1:1, used by `check_structure.py` and most of `check_safety.py`).
- **Delegated binding:** rule lives within a generic `_check_file` or similar (used by `check_idioms.py`, `check_shellcheck.py`, `check_size.sh`); the binding is documented in the script's docstring or in a registry, not the function name.
- **External-tool binding:** the script wraps an external tool (`check_shellcheck.py` wraps `shellcheck`; `check_shfmt.sh` wraps `shfmt`); the rule ids correspond to the external tool's rule codes.

The audit should accept any of these but flag scripts where the binding is undocumented (no docstring listing implemented rules; no registry).

---

## Recompose surprises

Populated during Tasks 2–4. Each entry: rule, surprise, resolution.

### Task 2 — template lock

**Tier-2 rules want a "Common fail signals" sub-list.** The unified Claude-rule template (per `rule-best-practices.md`) shows imperative + Why + How to apply + optional example + Exception. For Tier-2 rules consumed by an LLM judge, an explicit "Common fail signals" sub-list inside or after "How to apply" gives the judge concrete patterns to flag. Added in `rule-output-discipline.md`. This is template enrichment, not template violation — the bullets read naturally as elaboration of How-to-apply.

**Tier-3 rules need an "Audit guidance" or "Applicability" subsection.** The `paths:` field captures "this rule applies when editing files matching X" but can't express "this rule fires only when multiple scripts are in scope." Cross-entity rules need a small note about scope/applicability that Tier-1 and Tier-2 rules don't. Added in `rule-cross-entity-collision.md`.

**The unified body shape works for all three tiers.** No `## Detection` / `## Repair` split was needed. Substance from `audit-dimensions.md` (definition) and `repair-playbook.md` (recipe) carried into the unified body without loss. Recompose was the right discipline, not verbatim move.

**Recommended template extensions** (carry into the rollout sweep template):
- Tier-1: imperative + Why + How to apply + example + optional Exception. (Standard.)
- Tier-2: imperative + Why + How to apply + example + Common fail signals (sub-list) + Exception. (Extended for LLM-judge rubric.)
- Tier-3: imperative + Why + How to apply + example + Audit guidance (sub-paragraph on applicability) + Exception. (Extended for cross-entity scope.)

### Tasks 3–5 — bulk authoring + hub + cleanup

**Combined-entry splits work cleanly.** SC2010/2012/2045 split into 3 files (`ls-grep-parsing`, `ls-instead-of-find`, `iterating-ls-output`) — each SC code has a distinct anti-pattern even when the repair recipe direction is shared. Same for SC2013/2162 (split into `for-line-in-cat`, `read-without-r`). Each split file uses cross-references in the body ("see also: rule-ls-instead-of-find.md") to keep the family discoverable. **Recommendation:** keep the split pattern in the rollout sweep — single SC code per file, body cross-links to siblings.

**File-shape rules (`size`, `line-length`) split cleanly even though they share a script.** `check_size.sh::check_file` emits findings for both rules; the rule files are independent because the conventions are orthogonal (one is about total length, the other about per-line length). The `script:` binding is many-to-one (script-to-rule), and that's fine — the binding lives in the script, not the rule frontmatter. **Recommendation:** issue #407's audit must support many-to-one bindings; naming-convention-only binding (`check_<rule_id>`) breaks here.

**Hub authoring discovered the RULERS softening.** While writing `_hub.md`'s Tier-2 framing block, recognized the citation should be softened per the cleanup recommendation in #409. Used direction-only form in the hub (no specific "11.5 points" claim). Other check-* skills citing this in their docs still need cleanup — that's #409's scope.

**SKILL.md `references:` array becomes long.** 41 entries (1 hub + 40 rules + 1 best-practices). This is the cost of the unified shape — Claude's skill loader is now told about every rule file. The alternative (just hub + best-practices, with the hub's TOC providing rule discovery) was considered but rejected because the rule files need to be eagerly loadable when Claude is editing bash scripts. **Future consideration:** if hub-generation tooling lands (a script that produces SKILL.md `references:` from disk state), the array becomes derived rather than hand-maintained. Out of pilot scope; potential follow-up.

**Per-rule commits create useful rollback boundaries.** 40 individual commits (one per rule file) plus 4 task milestones. The granular-revert design held up — if any single rule's recompose turned out wrong, reverting one commit fixes it without disturbing the others. **Recommendation for sweep:** keep the per-file commit discipline in #408. Commit messages of the form `docs(<skill>): add rule file <id>` are short and grep-able.

---

## Rollout recommendations

Actionable changes for sweep [#408](https://github.com/bcbeidel/toolkit/issues/408) and the scaffolder/audit follow-ups.

### Templates (per-tier shape)

The single unified shape (per `rule-best-practices.md`) is the right baseline. Three tier-specific extensions improve fit:

- **Tier-1:** Standard shape (imperative + Why + How to apply + example + optional Exception). Body 1.5–2K. Detection lives in a script; rule body is the convention documentation + repair recipe.
- **Tier-2:** Add **Common fail signals** sub-list inside or after How-to-apply. Gives the LLM judge concrete patterns to flag. Body 2.5–3K.
- **Tier-3:** Add **Audit guidance** subsection covering applicability scope (when does the rule fire?). Body 2.5–3K.

Issue [#406](https://github.com/bcbeidel/toolkit/issues/406) (build-skill scaffolder) should generate per-tier templates with these structural variants — not a single template applied uniformly.

### Authoring discipline

- **Substance, not bytes.** "Verbatim move" doesn't apply with the unified shape — recompose audit prose ("Signal X — fix by doing Y") into convention prose ("Do X. Why: ... How to apply: ..."). The substance must be preserved exactly; the framing is what shifts.
- **Per-rule commits** (`docs(<skill>): add rule file <id>`) for granular revert. 40 commits for the pilot was tractable and useful.
- **Combined-entry splits** are first-class — each SC code or each composite rule gets its own file, cross-linked in the body. Don't merge unrelated rules to reduce file count.
- **Time budget:** ~5–10 min per Tier-1 rule, ~15–20 min per Tier-2 rule, ~15 min per Tier-3 rule. Pilot took roughly 8–10 hours of focused authoring work for `check-bash-script` (40 rules); budget similar per skill for the sweep.

### Audit infrastructure changes

Issue **#407** (`check-skill` audit recognition) needs richer mapping than naming-convention bindings — `check-bash-script` has multiple cases where one script function emits findings for several rules:
- `check_idioms.py::_check_file` emits findings for `bracket-test`, `printf-over-echo`, `var-braces`.
- `check_shellcheck.py::_check_file` delegates 15 rules to the `shellcheck` binary.
- `check_size.sh::check_file` emits findings for `size` and `line-length`.

Recommendations:
1. Don't enforce strict `check_<rule_id>` naming. Accept many-to-one (one function → many rules) and one-to-many (one rule → multiple functions across scripts).
2. The audit can validate the binding via a per-script docstring or a registry file (e.g., `scripts/_rules.json` mapping rule_id → script::function). Pilot did not introduce a registry; record this as an open design question for #407.
3. Audit should validate frontmatter has non-empty `name` and `description`, body has `**Why:**` and `**How to apply:**` markers. Flag rule files missing either.

### Hub structure

The hub (`_hub.md`) should:
- Group rules by tier (Deterministic / Judgment / Cross-Entity) with section headers.
- Lead with cross-rule framing (RULERS guidance, Tier-1 short-circuit, default-closed evaluator policy, missing-tool degradation, one-finding-per-dimension cap, cross-entity applicability). These are conventions the LLM judge needs that don't fit per-rule.
- Use one-line bullets per rule with a short description. Keep the hub itself well under 10K (the pilot's hub is 6.8K).
- **Soften RULERS citation** (per #409) — direction-only, no specific "11.5 points" claim.

### SKILL.md `references:` array

The array became long (41 entries). Two paths:
1. **Hand-maintained** (the pilot's choice). Acceptable for now; alphabetical order is stable and reviewable.
2. **Generated** from disk state by a small script. Future work — would let new rules be auto-discovered. Not in pilot scope.

The sweep should use option 1 unless a generation tool lands first.

### Distribution model (out of scope but worth noting)

Per-rule files at `references/rule-*.md` are plugin-distributed. Claude reads them ambiently when `paths:` matches. A toolkit-internal `.claude/rules/bash-scripts.md` pointer file would give Claude ambient guidance when editing bash scripts in the toolkit repo itself; a similar pointer in user projects would do the same for them. This is the rule + audit pairing pattern endorsed by `rule-best-practices.md`. Not in pilot scope; flag as a future follow-up issue.

---

## Cross-skill rule duplication observations

Surface impressions only — not a rigorous comparison. Rules in `check-bash-script` whose names/topics likely repeat in `check-skill`, `check-python-script`, `check-rule`, or `check-readme`. Input to a future `_shared/references/` extraction decision (separate plan, not Stage 1).

### High-confidence duplicates (almost certainly repeat verbatim or near-verbatim)

- **`secret`** — appears in `check-skill`, `check-python-script`, `check-readme`, probably others. Same regex-based detection, same recipe (externalize to env var with `${VAR:?MESSAGE}`).
- **`size`** / **body-length** — `check-skill` and `check-python-script` both have a body-length rule (warn at one threshold, fail at another). The threshold values differ but the convention is the same.
- **`line-length`** — likely in `check-skill`, `check-python-script`, possibly `check-rule`. Same 100-char convention typically; some skills may use 120.
- **`commenting-intent`** (Tier-2 D7) — `check-skill` and `check-python-script` likely have an analogous "comments explain why, not what" judgment dimension.
- **`naming`** (Tier-2 D6) — `check-python-script` definitely has a naming dimension (snake_case vs ALLCAPS conventions). Different language, similar shape.
- **`function-design`** (Tier-2 D5) — `check-python-script` has analogous "function cohesion" rules. Same rubric, different language.

### Likely duplicates (similar topics, may differ in detail)

- **`output-discipline`** (Tier-2 D1) — Python scripts also have stdout/stderr conventions, though the patterns are slightly different (`print` vs `sys.stderr.write`).
- **`input-validation`** (Tier-2 D2) — every script-family check-* skill likely has a "validate inputs early" dimension. The specifics (argparse vs `${var:?}`) differ but the principle is shared.
- **`subprocess-tool-hygiene`** (Tier-2 D3) — Python's analog is "preflight imports" or "verify external tools at import time." Different patterns; same intent.

### Implications for future `_shared/references/` extraction

A reasonable extraction for the duplicates above:

- **Cross-script-family Tier-1 rules** (`secret`, `size`, `line-length`) could live at `_shared/references/rule-secret.md`, etc., with each check-* skill's `SKILL.md references:` array enumerating the shared file. Risk: shared rule body might not fit each language's nuances perfectly. Mitigation: make the shared rule body language-agnostic (focus on the convention, not the syntax); per-language exceptions go in per-skill rules that "extend" the shared base.
- **Cross-language Tier-2 dimensions** (`commenting-intent`, `naming`, `function-design`, `output-discipline`) similarly extractable. Body would be language-agnostic; LLM judge applies the rubric to whichever language the artifact is in.

This is a substantial architectural decision — affects authoring workflow, audit machinery, and the question of how language-specific exceptions get layered onto shared rules. **Not pilot scope.** Recommended separate plan after sweep #408 lands; the sweep gives concrete data on what duplications exist (the surface impressions above need verification).
