---
name: check-github-workflow
description: >
  Audits a GitHub Actions workflow YAML file (or a directory under
  `.github/workflows/`) against 30 deterministic checks (top-level
  `name:`, permissions, timeouts, concurrency, SHA-pinning for every
  `uses:`, no `@main`/`@master`/floating refs, `pull_request_target`
  + PR checkout combo, template injection in `run:`, deprecated
  commands, secrets-in-top-env, fork-PR secret exposure, harden-runner
  first, persist-credentials, strict bash, actionlint, zizmor,
  yamllint, shellcheck on extracted `run:` content) plus seven
  judgment dimensions. Use when the user wants to "audit a github
  workflow", "lint my workflow", or "run zizmor on this". Not for
  composite actions — different rubric.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path]"
user-invocable: true
references:
  - ../../_shared/references/github-workflow-best-practices.md
  - references/check-correctness-and-error-handling.md
  - references/check-maintainability.md
  - references/check-performance-and-concurrency.md
  - references/check-permissions-and-secrets-discipline.md
  - references/check-pinning-and-supply-chain-posture.md
  - references/check-runtime-safety.md
  - references/check-trigger-discipline.md
license: MIT
---

# Check GitHub Workflow

Audit a GitHub Actions workflow file for structural soundness, safety posture, pinning discipline, and adherence to the authoring rubric. The rubric lives in [github-workflow-best-practices.md](../../_shared/references/github-workflow-best-practices.md).

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 9 scripts emitting JSON envelopes via `_common.py` (30 rule_ids total). Tier-2 has 7 judgment dimensions read inline by the primary agent. No Tier-3 cross-entity rule for this skill (workflows audit individually).

## When to use

Also fires when the user phrases the request as:

- "check this workflow"
- "review my github actions"
- "is this workflow safe"

## Workflow

### 1. Scope

Read `$ARGUMENTS`. Resolve to a `.github/workflows/*.yml` file or a directory containing workflows. Confirm scope aloud.

### 2. Tier-1 Deterministic Checks

Invoke 9 detection scripts:

```bash
SCRIPTS="${SKILL_DIR}/scripts"
TARGETS="$ARGUMENTS"

python3 "$SCRIPTS/check_secrets.py"     $TARGETS   # 1 rule:  secret (FAIL)
python3 "$SCRIPTS/check_structure.py"   $TARGETS   # 9 rules: workflow-name, job-name, step-name, permissions-top, timeout-minutes, defaults-shell, concurrency-group, concurrency-deploy, id-kebab
python3 "$SCRIPTS/check_pinning.py"     $TARGETS   # 5 rules: sha-pin-third-party, sha-pin-first-party, no-floating-ref, docker-tag, runner-pin-deploy
python3 "$SCRIPTS/check_safety.py"      $TARGETS   # 9 rules: pr-target-checkout, template-injection, deprecated-cmds, workflow-env-secrets, fork-pr-secrets, self-hosted-public-pr, strict-bash, persist-credentials, harden-runner-first
python3 "$SCRIPTS/check_shellcheck.py"  $TARGETS   # 1 rule:  shellcheck-run; inapplicable when shellcheck absent
python3 "$SCRIPTS/check_size.py"        $TARGETS   # 2 rules: run-block-size, workflow-size
bash    "$SCRIPTS/check_actionlint.sh"  $TARGETS   # 1 rule:  actionlint; inapplicable when absent
bash    "$SCRIPTS/check_zizmor.sh"      $TARGETS   # 1 rule:  zizmor; inapplicable when absent
bash    "$SCRIPTS/check_yamllint.sh"    $TARGETS   # 1 rule:  yaml-valid; inapplicable when absent
```

Each script emits a JSON array of envelopes. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (30 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_secrets.py` | `secret` | fail |
| `check_structure.py` | `permissions-top`, `timeout-minutes`, `concurrency-deploy` | fail |
| `check_structure.py` | `workflow-name`, `job-name`, `step-name`, `defaults-shell`, `concurrency-group`, `id-kebab` | warn |
| `check_pinning.py` | `sha-pin-third-party`, `no-floating-ref`, `docker-tag` | fail |
| `check_pinning.py` | `sha-pin-first-party`, `runner-pin-deploy` | warn |
| `check_safety.py` | `pr-target-checkout`, `template-injection`, `deprecated-cmds`, `workflow-env-secrets`, `fork-pr-secrets`, `self-hosted-public-pr` | fail |
| `check_safety.py` | `strict-bash`, `persist-credentials`, `harden-runner-first` | warn |
| `check_shellcheck.py` | `shellcheck-run` | warn |
| `check_size.py` | `run-block-size`, `workflow-size` | warn |
| `check_actionlint.sh` | `actionlint` | warn |
| `check_zizmor.sh` | `zizmor` | warn |
| `check_yamllint.sh` | `yaml-valid` | warn |

The previously-INFO `harden-runner-first`, `run-block-size`, and `workflow-size` rules are remapped to `warn` (the pattern has no INFO).

**Tier-2 exclusion list.** Any FAIL in `secret`, `permissions-top`, `timeout-minutes`, `concurrency-deploy`, `sha-pin-third-party`, `no-floating-ref`, `docker-tag`, `pr-target-checkout`, `template-injection`, `deprecated-cmds`, `workflow-env-secrets`, `fork-pr-secrets`, or `self-hosted-public-pr` excludes the workflow from Tier-2.

**Missing-tool degradation.** `check_shellcheck.py`, `check_actionlint.sh`, `check_zizmor.sh`, and `check_yamllint.sh` emit envelopes with `overall_status: inapplicable` and exit 0 when their respective tools are absent. Other scripts continue.

### 3. Tier-2 Judgment Dimensions

For each workflow that passed the Tier-2 exclusion gate, evaluate against the **7 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-trigger-discipline.md](references/check-trigger-discipline.md) | D1 — triggers scoped to actual need; `pull_request_target` justified | warn |
| [check-permissions-and-secrets-discipline.md](references/check-permissions-and-secrets-discipline.md) | D2 — least-privilege permissions; secrets scoped narrowly | warn |
| [check-pinning-and-supply-chain-posture.md](references/check-pinning-and-supply-chain-posture.md) | D3 — pin discipline; Dependabot governance | warn |
| [check-runtime-safety.md](references/check-runtime-safety.md) | D4 — strict bash; harden-runner; no shell injection | warn |
| [check-correctness-and-error-handling.md](references/check-correctness-and-error-handling.md) | D5 — `if:` guards meaningful; failure-handling explicit | warn |
| [check-performance-and-concurrency.md](references/check-performance-and-concurrency.md) | D6 — concurrency posture deliberate; caches deterministic | warn |
| [check-maintainability.md](references/check-maintainability.md) | D7 — names are developer-facing; long blocks extracted | warn |

#### Evaluator policy

- **Single locked-rubric pass per workflow.** Read all 7 rule files first, then evaluate the workflow in one LLM call.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`.
- **Severity floor: WARN.**
- **One finding per dimension maximum.**

### 4. Tier-3

No Tier-3 cross-entity rule for this skill. Workflows audit individually; cross-workflow concerns (duplicated logic, naming collisions across `.github/workflows/`) are handled by `/build:check-skill` for the workflow author's wider repo, not by this skill.

### 5. Report

Merge findings from Tier-1 + Tier-2 into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2. Each `Recommendation:` line copies through `recommended_changes` verbatim.

### 6. Opt-In Repair Loop

Ask once: "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:
- **Direct edit** — SHA pin, permissions block, timeout-minutes, harden-runner step. Show diff; write on confirmation.
- **Routed to another skill** — substantial rewrites → `/build:build-github-workflow`.
- **Tier-2 judgment** — ask the user; rewrite the section; show diff.

After each fix, re-run the relevant Tier-1 script.

## Anti-Pattern Guards

1. **Per-dimension LLM call.** Collapse into one locked-rubric call per workflow.
2. **LLM-evaluating format compliance.** YAML shape, pin syntax, permissions presence — handle deterministically.
3. **Ambiguous compliance reported as PASS.** Surface as WARN.
4. **Bulk-applying fixes.** Per-finding confirmation required.
5. **Re-evaluating scripted rules in Tier-2.** Trust the `pass` envelope.
6. **Suppressing the inapplicable envelope.** When `actionlint`/`zizmor`/`yamllint`/`shellcheck` is absent, the corresponding envelope emits `inapplicable` — surface them.
7. **Embellishing scripts' `recommended_changes`.** Copy through; do not paraphrase.

## Key Instructions

- Run Tier-1 deterministic checks first; gate LLM evaluation on structural validity.
- The 4 wrapper scripts (`actionlint`, `zizmor`, `yamllint`, `shellcheck`) gracefully degrade to `inapplicable` when their tools are absent.
- Recovery: read-only outside the Repair Loop.

## Handoff

**Chainable to:** `/build:build-github-workflow` (rebuild non-compliant workflows from scratch).
