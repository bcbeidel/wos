---
name: Hook/Shell `--as-tool` Delegation
description: Refactor build-hook and check-hook to delegate shell-script concerns to build-shell and check-shell via the --as-tool invocation pattern; opt all four skills into skill-invocable mode.
type: design
status: draft
related:
  - plugins/build/_shared/references/as-tool-contract.md
  - plugins/build/skills/build-skill/references/as-tool-scaffolding.md
  - plugins/dummy/skills/greet/SKILL.md
---

# Hook/Shell `--as-tool` Delegation

## Purpose

The hook pair (`build-hook`, `check-hook`) currently carries its own shell scaffolding template and its own shell-hygiene lints. The shell pair (`build-shell`, `check-shell`) already owns the authoritative version of both. This design routes the overlap through the `--as-tool` invocation contract that shipped in build-0.5.0 (PR #335): shell concerns are generated and audited once by the shell pair, and the hook pair calls into them.

**Why now.** The `--as-tool` pattern is settled and empirically validated (issue #327 closed the probe via the `dummy` plugin, PR #334). The hook/shell boundary is the first real consumer — forcing the pattern's first multi-artifact caller and its first caller-of-caller delegation.

**Closes #327.**

## Non-goals

- Re-litigating any aspect of the `--as-tool` contract (parsing rule, envelope shapes, emission rules). The shared spec is authoritative.
- Migrating any other skill to opt into `--as-tool`.
- Touching the `dummy` plugin.
- Changing unrelated `build` skills (`build-skill`, `build-rule`, `build-subagent`, `refine-prompt`, and their `check-*` peers).

## In scope

Four skills change. One lint catalog gains one entry. One plugin version bumps.

### Surface changes per skill

**`build-shell`** — opts into `skill-invocable: true`; adds a `## --as-tool contract` section; splits its final workflow step into human and `--as-tool` branches. Return shape: **ARTIFACT** (`text/x-shellscript`). FX.1 scope-gate refusals return structured `Refusal` under `--as-tool` instead of halting.

**`check-shell`** — opts into `skill-invocable: true`; adds a `## --as-tool contract` section; splits Report step into human (table + preamble) and `--as-tool` (DATA envelope) branches. Return shape: **DATA**. Adds lint **S11: missing strict-mode preamble (warn)** to close a delegation gap.

**`build-hook`** — opts into `skill-invocable: true`; adds a `## --as-tool contract` section; Draft step becomes a caller: derives `build-shell` intake from the hook's context, invokes `/build:build-shell --as-tool`, layers hook-specific content onto the returned scaffold, and emits a MULTI-ARTIFACT Success with two fenced blocks (the hook script and the settings.json entry). Return shape: **ARTIFACT** (`text/x-shellscript, application/json`).

**`check-hook`** — opts into `skill-invocable: true`; adds a `## --as-tool contract` section; Checks step becomes a caller: for each `"type": "command"` hook script, invokes `/build:check-shell --as-tool` and merges its findings with the retained hook-specific checks. Removes delegated checks (full removal of 14; partial removal of 11, 12, 15). Return shape: **DATA**.

## Required fields per skill (under `--as-tool`)

| Skill | Required fields | Notes |
|---|---|---|
| `build-shell` | `target-shell`, `purpose`, `invocation-style`, `setuid`, `deps` | `save-path` stays human-mode-only; `--as-tool` callers own the Save step. |
| `check-shell` | `path` | Script path only; tool detection and target inference run internally. |
| `build-hook` | `hook-event`, `handler-type`, `enforcement-goal`, `matcher` | `matcher` always required; callers pass `"*"` for non-tool events. Inner `build-shell` call is pinned to `target-shell=bash-3.2-portable`. |
| `check-hook` | `settings-path` | Path to `.claude/settings.json` or equivalent; no default under `--as-tool` (human mode retains the dual-path default). |

Missing required fields hard-fail with `NeedsMoreInfo`.

## Return envelopes

### `build-shell` (ARTIFACT)

```
{"type": "Success", "artifact_types": ["text/x-shellscript"], "metadata": {"target_shell": "bash-3.2-portable", "invocation_style": "cli"}}
```
```bash
#!/usr/bin/env bash
# ... scaffold ...
```

Scope-gate refusal (FX.1 signal fired) returns `Refusal` with `category: "scope-gate"`; retryable only when the caller changes the inputs that tripped the signal.

### `check-shell` (DATA)

```json
{"type": "Success", "value": {
  "path": "scripts/foo.sh",
  "target_shell": "bash-3.2-portable",
  "summary": {"fail": 2, "warn": 3, "total": 5},
  "findings": [
    {"group": "Safety", "lint": "S1", "severity": "fail", "line": 57, "message": "..."},
    {"group": "Documentation", "lint": "D1", "severity": "warn", "line": null, "message": "..."}
  ],
  "external_tools": {
    "shellcheck":     {"present": true,  "output": "..."},
    "shfmt":          {"present": false, "install_hint": "..."},
    "checkbashisms":  {"present": false, "install_hint": "..."}
  }
}}
```

Severity ∈ `{fail, warn}`; identical to the human-mode catalog. External-tool output is raw per-tool so the caller can surface it verbatim. `line` is nullable for file-level findings.

### `build-hook` (MULTI-ARTIFACT)

```
{"type": "Success", "artifact_types": ["text/x-shellscript", "application/json"], "metadata": {"hook_event": "PreToolUse", "matcher": "Bash", "handler_type": "command"}}
```
```bash
#!/usr/bin/env bash
# ... hook script (inner build-shell scaffold + hook-specific injections) ...
```
```json
{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/<name>.sh", "timeout": 60}]}]}}
```

`metadata` carries exactly three keys: `hook_event`, `matcher`, `handler_type`. Everything else the caller needs is in the settings.json block.

### `check-hook` (DATA)

```json
{"type": "Success", "value": {
  "settings_path": ".claude/settings.json",
  "summary": {"fail": 1, "warn": 4, "total": 5},
  "findings": [
    {"source": "check-hook", "check": "4", "severity": "fail", "event": "Stop", "hook": ".claude/hooks/stop.sh", "message": "..."},
    {"source": "check-shell", "lint": "S1", "severity": "fail", "hook": ".claude/hooks/gate.sh", "line": 12, "message": "..."}
  ]
}}
```

Findings merge hook-retained checks with `check-shell` output per script. `source` field identifies which skill authored each finding so the reader can trace ownership.

## Delegation boundary (`check-hook` Option X)

**Delegated to `check-shell` (fully removed from `check-hook`):**
- Check 14 (ShellCheck / shfmt)
- Check 11 (strict-mode preamble + `|| true` guards)
- Check 15 (script style: stderr, `[[` vs `[`, `set -x`, shebang form)
- Check 12's unquoted-variable portion (maps to `check-shell` S1)

**Retained in `check-hook` (hook-specific semantics):**
- 1 PreToolUse gap
- 2 Destructive operations (`rm -rf`, `git push --force`, etc.)
- 3 Async + blocking contradiction
- 4 Stop hook loop risk
- 5 `INPUT=$(cat)` and executable bit
- 6 Tool-name case + `$HOME`/`~` path expansion
- 7 PostToolUse enforcement intent
- 8 Rule overlap vs. CLAUDE.md
- 9 Idempotency (hook-frequency-sensitive)
- 10 Latency risk
- 12 (eval-on-payload portion only)
- 13 `jq` availability + `tool_input` field-path correctness
- 16 settings.json attack surface

Shell-hygiene findings surface under `source: "check-shell"`; hook-specific findings under `source: "check-hook"`. Single ownership per lint — no duplication, no "amplifier" framing.

## New lint: `check-shell` S11

Category: Safety. Severity: warn.

**S11. Missing strict-mode preamble.** Script does not begin (after the shebang and header) with `set -Eeuo pipefail` (bash) or `set -eu` (posix-sh). Without strict mode, commands that exit non-zero proceed silently and unset-variable dereferences expand to empty strings, producing actions on wrong inputs. Fix: add the appropriate strict-mode line near the top of the script. The `check-shell` scaffold template already emits it; S11 catches hand-rolled or legacy scripts that skipped it.

This lint closes the delegation gap: `check-hook` check 11 had this as part of its preamble audit; without an equivalent in `check-shell`, full delegation would lose coverage.

## Parallel-safety

- `build-shell`, `build-hook`: **parallel-safe** (pure computation; Save is skipped under `--as-tool`).
- `check-shell`: **parallel-safe** (read-only file inspection; no shared state).
- `check-hook`: **not parallel-safe when invoked with overlapping `settings-path` values** — multiple concurrent calls against the same settings file produce redundant work but no correctness issue; document as "safe, but redundant" rather than serialize.

## Plugin version bump

`plugins/build` 0.5.0 → **0.6.0**. Minor bump — behavioral change to four existing skills, no breaking change to the human-mode invocation surface.

Updates: `plugins/build/.claude-plugin/plugin.json`, `plugins/build/pyproject.toml`.

## Acceptance criteria

1. All four skills declare `skill-invocable: true` and carry a conforming `## --as-tool contract` section.
2. `/build:check-skill --as-tool` passes checks 23-31 on all four SKILL.md files.
3. `build-shell --as-tool target-shell=bash-3.2-portable purpose="demo" invocation-style=cli setuid=no deps=jq,curl` emits a valid ARTIFACT envelope + one `bash` fenced block.
4. `check-shell --as-tool path=<script>` emits a DATA envelope matching the schema above.
5. `build-hook --as-tool hook-event=PreToolUse handler-type=command enforcement-goal="block rm -rf" matcher=Bash` emits a valid MULTI-ARTIFACT envelope + `bash` and `json` fenced blocks in that order.
6. `check-hook --as-tool settings-path=.claude/settings.json` emits a DATA envelope merging `check-shell` and `check-hook` findings, labeled by `source`.
7. `check-shell` human-mode report surfaces S11 as a warn when the preamble is missing.
8. `check-hook` no longer runs delegated checks in its own scan; those findings appear only via the inner `check-shell` call.
9. Plugin version at `0.6.0` in both manifests.
10. Superseded plan `.plans/2026-04-19-hook-shell-structured-invocation.plan.md` referenced in the new plan's history as pre-refinement (branch `explore/327-structured-invocation-thinking`).

## Constraints

- No changes to the shared `--as-tool` contract file; this design consumes the contract as-is.
- No auto-patching of `settings.json` in either mode — `build-hook` emits the settings block but the write step stays with the user (human) or caller (`--as-tool`).
- `build-hook`'s inner `build-shell` invocation pins `target-shell=bash-3.2-portable`. A future revision may expose this as a caller-supplied field; out of scope here.
- `check-hook` S11 passes through from `check-shell` under `source: "check-shell"` — do not re-surface it as a native `check-hook` finding.

## Open questions

None. All four surfaced decisions settled during scoping:
1. Required fields per skill → five/one/four/one (A, A, B, single-field).
2. Multi-artifact metadata → three keys only (A).
3. `check-shell` findings schema → flat, two-tier severity (A).
4. Delegation boundary → full delegation on overlap, add S11 (X).
