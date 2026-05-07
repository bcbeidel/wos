---
name: check-pre-commit-config
description: >
  Audits a `.pre-commit-config.yaml` (and referenced local hook
  scripts) against 20 deterministic checks (YAML shape, `rev:`
  pinning, scope declarations, network-call / destructive-command /
  error-suppression patterns, shell-script strict mode, hook
  explicit-name and require-serial hygiene) plus seven judgment
  dimensions and a Tier-3 cross-config collision check. Use when the
  user wants to "audit pre-commit", "lint pre-commit", or "review my
  pre-commit hooks". Not for hand-rolled `.git/hooks/` — out of
  scope. Not for CI pipelines — route elsewhere.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path-to-repo-root-or-config-file]"
user-invocable: true
references:
  - ../../_shared/references/pre-commit-config-best-practices.md
  - references/check-collision.md
  - references/check-developer-experience.md
  - references/check-error-handling-and-messaging.md
  - references/check-hook-structure.md
  - references/check-performance-intent.md
  - references/check-reproducibility.md
  - references/check-safety-posture.md
  - references/check-scope-discipline.md
license: MIT
---

# Check Pre-Commit Config

Audit a `.pre-commit-config.yaml` — plus the local shell/Python scripts it invokes — for reproducibility, scope, safety, error handling, and adherence to the `pre-commit` framework's conventions. The rubric lives in [pre-commit-config-best-practices.md](../../_shared/references/pre-commit-config-best-practices.md).

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 6 scripts emitting JSON envelopes via `_common.py` (20 rule_ids total). Tier-2 has 7 judgment dimensions read inline by the primary agent. Tier-3 is `collision` (cross-config duplication).

## When to use

Also fires when the user phrases the request as:

- "check .pre-commit-config.yaml"
- "is my pre-commit config safe"
- "what's wrong with my pre-commit"

## Workflow

### 1. Scope

Read `$ARGUMENTS`. Resolve to a `.pre-commit-config.yaml` (or `.yml`) at the path or repo root. Confirm scope aloud.

### 2. Tier-1 Deterministic Checks

Invoke 6 detection scripts:

```bash
SCRIPTS="${SKILL_DIR}/scripts"
TARGET="$ARGUMENTS"   # path to .pre-commit-config.yaml

python3 "$SCRIPTS/check_yaml_shape.py"            $TARGET   # 4 rules: config-missing, yaml-parse, repos-key, hook-shape (FAIL)
python3 "$SCRIPTS/check_rev_pinning.py"           $TARGET   # 2 rules: floating-rev (FAIL), rev-shape (WARN)
python3 "$SCRIPTS/check_hook_scope.py"            $TARGET   # 2 rules: hook-scope, pass-filenames-false (WARN)
python3 "$SCRIPTS/check_safety.py"                $TARGET   # 5 rules: network-io, destructive-git, destructive-shell, sudo, error-suppression (all FAIL)
bash    "$SCRIPTS/check_script_strictness.sh"     <referenced .sh files>   # 1 rule: shell-strictness (FAIL)
python3 "$SCRIPTS/check_hygiene.py"               $TARGET   # 6 rules: min-version, lang-version-pin, hook-id, local-hook-name, require-serial, builtin-duplication
```

Each script emits a JSON array of envelopes. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (20 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_yaml_shape.py` | `config-missing`, `yaml-parse`, `repos-key`, `hook-shape` | fail |
| `check_rev_pinning.py` | `floating-rev` | fail |
| `check_rev_pinning.py` | `rev-shape` | warn |
| `check_hook_scope.py` | `hook-scope`, `pass-filenames-false` | warn |
| `check_safety.py` | `network-io`, `destructive-git`, `destructive-shell`, `sudo`, `error-suppression` | fail |
| `check_script_strictness.sh` | `shell-strictness` | fail |
| `check_hygiene.py` | `hook-id` | fail |
| `check_hygiene.py` | `min-version`, `lang-version-pin`, `local-hook-name`, `require-serial`, `builtin-duplication` | warn |

**Tier-2 exclusion list.** Any FAIL in `config-missing`, `yaml-parse`, `repos-key`, `hook-shape`, `floating-rev`, any safety rule (`network-io`, `destructive-git`, `destructive-shell`, `sudo`, `error-suppression`), `shell-strictness`, or `hook-id` excludes the config from Tier-2.

### 3. Tier-2 Judgment Dimensions

For each config that passed the Tier-2 exclusion gate, evaluate against the **7 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-reproducibility.md](references/check-reproducibility.md) | D1 — pinned versions; deterministic across machines | warn |
| [check-scope-discipline.md](references/check-scope-discipline.md) | D2 — hooks scoped to relevant files via files/types | warn |
| [check-safety-posture.md](references/check-safety-posture.md) | D3 — no network I/O, history rewrites, destructive ops | warn |
| [check-error-handling-and-messaging.md](references/check-error-handling-and-messaging.md) | D4 — exit codes communicate intent; messages name the failing operation | warn |
| [check-performance-intent.md](references/check-performance-intent.md) | D5 — file-mutating hooks declare require_serial | warn |
| [check-developer-experience.md](references/check-developer-experience.md) | D6 — names + ids developer-facing; minimum_pre_commit_version pinned | warn |
| [check-hook-structure.md](references/check-hook-structure.md) | D7 — repo entries grouped logically; one concern per hook | warn |

#### Evaluator policy

- **Single locked-rubric pass per config.** Read all 7 rule files first, then evaluate the config in one LLM call.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`, not `pass`.
- **Severity floor: WARN.** All 7 Tier-2 dimensions are coaching, not blocking.
- **One finding per dimension maximum.**

### 4. Tier-3 Cross-Config Collision

Evaluate against [check-collision.md](references/check-collision.md). For multi-repo audits or org-wide scans, surface duplicate hook definitions / boilerplate across configs as `warn`. Single-config scope returns `inapplicable`.

### 5. Report

Merge findings from all 3 tiers into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3 within severity. Each `Recommendation:` line copies through `recommended_changes` verbatim.

### 6. Opt-In Repair Loop

Ask once:

> "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:

- **Direct edit** — `rev:` pin, hook id/name, files/types scope, `require_serial: true`. Show diff; write on confirmation.
- **Routed to another skill** — substantial rewrites → `/build:build-pre-commit-config`.
- **Tier-2/3 judgment** — ask the user; rewrite the section; show diff; write on confirmation.

After each applied fix, re-run the relevant Tier-1 script. Terminate when the user enters `n` or exhausts findings.

## Anti-Pattern Guards

1. **Per-dimension LLM call.** Collapse into one locked-rubric call per config.
2. **LLM-evaluating format compliance.** YAML shape, rev pinning, hook id presence — handle deterministically in Tier-1.
3. **Ambiguous compliance reported as PASS.** Surface as WARN (default-closed).
4. **Bulk-applying fixes.** Per-finding confirmation required.
5. **Re-evaluating scripted rules in Tier-2.** Scripts are authoritative for the 20 Tier-1 rules.
6. **Suppressing the inapplicable envelope.** When the cisco scanner / external tools are missing, surface `inapplicable`.
7. **Embellishing scripts' `recommended_changes`.** Each rule's recipe constant is canonical guidance.

## Key Instructions

- Run Tier-1 first; gate LLM evaluation on structural validity.
- Present all 7 Tier-2 dimensions as a single locked-rubric call.
- Include the full config and referenced scripts verbatim in LLM evaluation.
- Recovery: read-only outside the Repair Loop.

## Handoff

**Receives:** Path to a `.pre-commit-config.yaml` or repo root containing one.

**Produces:** A unified findings table merging the 20 Tier-1 envelopes (script JSON), 7 Tier-2 judgment findings per config, and Tier-3 cross-config collision findings (multi-config scope only). Each row: tier, rule_id, location, status, reasoning + `recommended_changes` excerpt.

**Chainable to:** `/build:build-pre-commit-config` (rebuild non-compliant config from scratch).
