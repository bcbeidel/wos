---
name: check-hook
description: >
  Audits Claude Code hooks configuration for event coverage, script safety,
  async and blocking contradictions, Stop hook loop risks, rule overlap,
  and idempotency. Use when the user wants to "audit hooks", "check hooks",
  "review hooks", "check my hooks", "what quality gates are missing", or
  "are my hooks safe".
argument-hint: "[settings.json path]"
user-invocable: true
skill-invocable: true
references:
  - references/platform-limitations.md
  - ../../_shared/references/as-tool-contract.md
---

# Check Hook

Inspect a project's Claude Code hooks configuration for coverage gaps,
misconfigurations, unsafe patterns, and redundancy. Read-only — reports
findings but does not modify any files.

Two invocation modes:

- **Human** — prompts for a path if none supplied, runs hook-specific
  checks, invokes `/build:check-shell` per command-hook script for
  shell-hygiene coverage, renders a merged findings table.
- **`--as-tool`** — skill-caller mode. Structured DATA emission per
  [`as-tool-contract.md`](../../_shared/references/as-tool-contract.md):
  a single JSON envelope with `findings` merged from `check-hook` and
  `check-shell` sources. Every finding carries `source:` so callers can
  trace ownership.

## 1. Input

If `$ARGUMENTS` is non-empty, read the settings file at that path. Otherwise,
read hooks from both of these default locations (use whichever exist):
- `.claude/settings.json`
- `.claude/settings.local.json`

If neither location exists, or neither contains a `hooks:` key, report
this as the first finding before running any checks:

> **No hooks configured** (warn) — No hooks found in `.claude/settings.json`
> or `.claude/settings.local.json`. PreToolUse hooks provide deterministic
> enforcement that CLAUDE.md instructions cannot guarantee.

Then continue to the Event coverage check, which will also fire.

## 2. Primitive Routing

Before running numbered checks, scan `CLAUDE.md` (if it exists) for rules that match any of the three conversion signals — rules that belong in hooks but are currently advisory only:

1. The rule is one Claude keeps violating under normal conditions
2. The rule can be expressed as a shell one-liner (format check, test gate, naming pattern)
3. The rule requires enforcement at a specific lifecycle moment (before a tool call, at session end)

For each matching rule found: flag as `warn`, quote the rule text, and note which signal it matches. Suggest converting to a PreToolUse hook.

## 3. Platform Scope

Run alongside the numbered checks in step 4. Cross-platform findings are appended as a separate section of the report in step 5.

These checks target Claude Code (`settings.json` / `settings.local.json`). If the project's hooks may run on additional platforms, read [platform-limitations.md](references/platform-limitations.md) and flag the relevant limitations in the report.

## 4. Checks

Run thirteen hook-specific checks, plus delegate shell-hygiene coverage
to `/build:check-shell` for every `"type": "command"` hook script.

**Delegation to `check-shell`.** For each hook whose entry has
`"type": "command"` and resolves to a script on disk, invoke:

    /build:check-shell --as-tool path=<resolved hook-script path>

Collect the returned `findings` and `external_tools` from each inner
call. Merge the findings into the outer report under `source:
"check-shell"`; retain the outer skill's findings under `source:
"check-hook"`. The external-tool Missing Tools preamble from
`check-shell` bubbles up unchanged — no hook-side tool detection
needed.

**Checks owned by `check-shell` (removed from this skill):**

- Script safety preamble (`set -Eeuo pipefail`, `|| true` guards) —
  covered by `check-shell` S11 + existing safety lints.
- ShellCheck / shfmt integration — covered by `check-shell`'s external-tool
  probe.
- Script style conventions (stderr vs stdout, `[[` vs `[`, `set -x`,
  shebang form) — covered by `check-shell`'s safety and style lints.
- Unquoted variable expansion on payload-derived values — covered by
  `check-shell` S1.

The thirteen retained checks below focus on *hook-specific* semantics:
tool_input payload handling, event-lifecycle correctness, blocking-intent
discipline, and Claude Code configuration attack-surface concerns.

### 1. No hooks / PreToolUse gap

Is a `PreToolUse` hook present?

`PreToolUse` is the only event that can block tool execution (via exit
code 2). Flag as `warn` if no `PreToolUse` hook is present, with a note that
quality-gate enforcement requires PreToolUse.

### 2. Script safety

For each hook using `"type": "command"`, read the command string. Flag
as `fail` if it contains:
- `rm -rf`
- `git reset --hard`
- `git checkout .`
- `git push --force` or `git push -f`

These operations are irreversible and should never run automatically
without explicit user intent.

### 3. Async + blocking contradiction

For each hook, check whether `"async": true` is set alongside a script
that contains `exit 2` logic, or is described as a gate or blocker.

Async hooks run in the background after execution proceeds — they can
never block regardless of exit code. A hook that needs to block must be
synchronous (the default; `async` omitted or `false`).

Flag as `fail` if `async: true` is paired with blocking intent.

Also flag as `warn` for Python hook scripts that use `sys.exit(1)` to signal validation failure, or that have no explicit `sys.exit(2)` in exception handlers. Python uncaught exceptions default to exit code 1 — non-blocking. A Python validator that throws exits 1, showing a hook error in the transcript while execution proceeds silently.

Also flag as `warn` if a hook writes structured JSON output (`hookSpecificOutput`, `systemMessage`, or raw stdout) that could exceed 10,000 characters in practice — hook stdout is capped at 10,000 characters and truncated silently, which corrupts structured JSON responses.

Also flag as `warn` if a hook emits JSON on stdout but any non-zero exit path precedes or follows the emission — Claude Code parses stdout only on exit 0; stdout on any non-zero exit is discarded, so a JSON block emitted on exit 2 is silently lost. For the same reason, flag as `warn` if a JSON-emitting hook omits `hookSpecificOutput.hookEventName` (spec-required field) or emits leading non-JSON text (e.g., `echo "info" ; jq -n '...'`) — "JSON validation failed" errors surface in the transcript with no block effect.

### 4. Stop hook loop risk

For any `Stop` or `SubagentStop` hook that may exit 2, check whether a re-entry guard is present.

**`SubagentStop`:** The payload includes a `stop_hook_active` boolean field. Check that the script reads this field and exits 0 when it is `True`. Without this guard, a blocking SubagentStop hook forces Claude to keep responding indefinitely.

**`Stop`:** The payload does not include `stop_hook_active` (it includes `stop_reason` instead). An equivalent re-entry guard is still required — check that the script uses a session-scoped mechanism (e.g., a temp file keyed to `session_id`) to detect and short-circuit repeated firing.

Flag as `fail` for any Stop or SubagentStop hook that may exit 2 but contains no re-entry guard of either form.

Also flag as `warn` for SubagentStop hooks that exit 2 and use `stop_hook_active` alone without inspecting `last_assistant_message` (the subagent's most recent output) for progress indicators. Spec recommends layering both: `stop_hook_active` shortcircuits the infinite re-fire, while the `last_assistant_message` check lets the block resolve naturally once the subagent satisfies the requirement — without it the hook remains a hard gate that the subagent cannot learn to pass.

### 5. Stdin correctness

For each `"type": "command"` hook, check whether the script body contains `INPUT=$(cat)` or equivalent stdin consumption. Scripts that skip this will hang or fail silently when the hook payload exceeds the OS pipe buffer — a common failure on large files. Flag as `warn`.

Also check that each command hook's script file is executable (`chmod +x`). A non-executable script silently fails with no distinguishing error from a hook that isn't loaded. Flag as `warn`. Also flag as `warn` if a hook command spawns a subshell and the project's shell profiles (`.bashrc`, `.zshrc`) contain unconditional output statements; output emitted during non-interactive hook execution is prepended to hook stdout and corrupts the JSON payload parse. Guard pattern: `if [[ $- == *i* ]]; then`.

### 6. Tool name case mismatch and path expansion

For each hook with a `matcher` field, verify the tool name uses exact canonical casing: `Bash`, `Write`, `Edit`, `MultiEdit`, `Read`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Agent`, `NotebookEdit`, `NotebookRead`. A matcher on `bash` or `write` silently matches nothing, disabling the hook without any error. Flag as `fail`.

Also check each hook's `"command"` field in `settings.json` for `$HOME` or `~`. Both have been observed to expand inconsistently across versions and silently fail to load the script; the spec's reference pattern is `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh` (or an absolute path), which resolves regardless of cwd. Flag as `warn`.

### 7. Enforcement intent on PostToolUse

`PostToolUse` fires after execution and cannot prevent it — a
`PostToolUse` hook intended to block is a misconfiguration that silently
fails to enforce. Flag as `warn` for any `PostToolUse` hook whose script
or description suggests a blocking or gating intent.

Also flag as `warn` if the project may run under `claude -p` and uses `AskUserQuestion` or `ExitPlanMode` without a `PreToolUse` hook that returns `permissionDecision: "allow"` plus an `updatedInput` supplying the answer. Per spec, those tools block in non-interactive mode; the documented workaround is a PreToolUse hook that pre-answers them. Enforcement logic that must fire under `-p` must be anchored on `PreToolUse`, not on interactive-only events.

Also flag as `warn` if more than one `PreToolUse` hook targeting the same tool name returns `updatedInput`. Hooks run in parallel; the last to finish wins. Multiple hooks rewriting the same tool's input produce non-deterministic results with no runtime warning — consolidate input modifications for a given tool into one hook.

Also flag as `warn` for any blocking `PreToolUse` hook (exit 2 paths present) that has no companion warning-only hook on the same matcher and no comment in the script indicating a prior warning phase has been completed. Best practice: deploy with `exit 1` (warn only) for at least a week before graduating to `exit 2` (block). One false positive per session is sufficient to establish a bypass habit that defeats the gate permanently.

Also flag as `warn` if user-level hooks (`~/.claude/settings.json`) exist alongside project hooks — user-level hooks fire in all projects, including CI automation. Enforcement designed for local use silently applies in GitHub Actions and other automated pipelines.

### 8. Rule overlap

Read `CLAUDE.md` (if it exists) and check whether any hook duplicates an
instruction already expressed there.

Overlap is not always wrong — a hook that enforces a CLAUDE.md rule
deterministically is intentional belt-and-suspenders. But one of the two
may be stale, or the hook may have been added without knowing the rule
already exists.

Flag as `warn` for each overlap found, noting which CLAUDE.md instruction
the hook may duplicate.

### 9. Idempotency

For each hook script, check for patterns that accumulate state across
invocations:
- Unbounded appending to a log file without rotation
- Incrementing a counter without a reset mechanism
- Creating files that are never cleaned up

Running a hook twice should produce the same result. State accumulation
is a sign the hook will degrade over time.

Flag as `warn` per pattern found.

### 10. Latency risk

For each synchronous hook (no `async: true`), check whether the command calls an LLM, makes a network request, or runs a slow external process (e.g., `curl`, `claude`, a Python script that imports large models). Synchronous hooks block Claude while they run; slow hooks create session sluggishness that accumulates across a session and generates pressure to bypass hooks entirely. Flag as `warn` for any hook whose command string suggests a network call or LLM invocation in the hot path.

### 11. Injection safety (hook-payload specific)

For each hook script, flag as `fail` if the script passes a payload-derived variable to `eval` (e.g., `eval "$command"` where `command` is extracted from `tool_input`). Hook payloads are user-influenced — `tool_input.command` in Bash hooks reflects what the user asked Claude to run — and `eval` on user-controlled data is a shell injection vector with no safe sanitization path.

Evidence suggests bare command names (`jq`, `grep`) are susceptible to PATH override in adversarial environments — flag as `warn` for hooks defined in project-level `settings.json` (where any collaborator with commit access can influence the environment) or hooks with evidence of CI usage (e.g., a `.github/` directory exists), where PATH may be injected by the build environment (MODERATE confidence from a single T5 source).

*(Generic unquoted-variable findings are delegated to `check-shell` S1
and surface under `source: "check-shell"` in the merged report.)*

### 12. jq availability and field path correctness

For each hook script that calls `jq`, check whether `jq` availability is verified before use (e.g., `command -v jq &>/dev/null`). Claude Code runs hooks with a restricted PATH; `jq` is not guaranteed on all systems. A missing `jq` causes the hook to fail in an uncontrolled way — silently passing (exit 0) or blocking everything (exit 2) — depending on script structure. Flag as `warn` if no availability check is present. Also check that jq field paths match the target tool's `tool_input` schema: `jq -r '.tool_input.command'` is correct for Bash hooks but returns `null` silently for Write hooks (`.tool_input.file_path`). Flag as `warn` for scripts whose matcher targets a tool whose `tool_input` structure differs from what the jq path assumes.

If the hook may run on Copilot, flag as `fail`: Copilot serializes tool arguments as `toolArgs` (a JSON string), not as `tool_input` (an object). Hooks using `jq '.tool_input.*'` fail silently on Copilot — cross-platform hooks require a platform detection branch or separate configurations.

*(ShellCheck and shfmt integration — previously checks 14 — are now
delegated to `check-shell`'s external-tool probe; findings surface
under `source: "check-shell"`. Generic script-style findings —
previously check 15: stderr vs stdout, `[[` vs `[`, `set -x`, shebang
form — are also delegated to `check-shell`.)*

### 13. settings.json as attack surface

Check whether hooks are defined in project-level `.claude/settings.json` (checked into the repo) versus `.claude/settings.local.json` (gitignored, personal only). Project-level hook entries execute automatically on any developer who opens the repo — a collaborator with commit access can inject arbitrary commands (CVE-2025-59536). Flag as `warn` for any hook in project `settings.json` that has not been treated with the same code-review scrutiny as executable source files. Flag as `warn` if security-sensitive hooks (credentials protection, command blocking) live in `settings.json` where they are also visible and modifiable by the full team — suggest moving personal-only enforcement to `settings.local.json`.

## 5. Report

### 5a. Human mode

Present findings as a table with a summary count at the top. Include a
`source` column so hook-specific findings (from `check-hook`) and
shell-hygiene findings (delegated to `check-shell`) are distinguishable
at a glance:

```
N issues across M hooks (X fail, Y warn)

source       | event          | hook command          | check             | finding
-------------+----------------+-----------------------+-------------------+---------------------------
check-hook   | PostToolUse    | .claude/hooks/gate.sh | Event coverage    | PostToolUse cannot block; use PreToolUse for enforcement
check-hook   | Stop           | .claude/hooks/stop.sh | Stop hook loop    | No stop_hook_active guard — infinite loop risk
check-shell  | -              | .claude/hooks/gate.sh | S1                | Unquoted ${TOOL_NAME} expansion (line 12)
check-hook   | PostToolUse    | lint-after-write.sh   | Async + blocking  | async:true with exit 2 — hook will never block
```

The `external_tools` Missing Tools preamble from `check-shell` surfaces
unchanged at the top of the report when any of `shellcheck` / `shfmt` /
`checkbashisms` is absent.

If cross-platform gaps were identified in Platform Scope, append a separate section to the report:
```
**Cross-platform limitations:** [list each platform and its specific gap]
```

If no issues are found, confirm:
> "Hooks look well-configured."

### 5b. `--as-tool` mode

Emit a single JSON envelope — no fenced blocks, no prose. Schema:

    {"type": "Success", "value": {
      "settings_path": ".claude/settings.json",
      "summary": {"fail": 1, "warn": 4, "total": 5},
      "findings": [
        {"source": "check-hook", "check": "4", "severity": "fail", "event": "Stop", "hook": ".claude/hooks/stop.sh", "line": null, "message": "No stop_hook_active guard — infinite loop risk"},
        {"source": "check-shell", "lint": "S1", "severity": "fail", "event": null, "hook": ".claude/hooks/gate.sh", "line": 12, "message": "Unquoted ${TOOL_NAME} expansion"}
      ],
      "external_tools": {
        "shellcheck": {"present": true, "output": "..."},
        "shfmt":      {"present": false, "install_hint": "..."}
      }
    }}

Rules:

- `source` ∈ `{"check-hook", "check-shell"}` on every finding — callers
  rely on it to attribute the finding to the owning skill.
- `check-hook` findings carry a `check` field (numeric, as a string);
  `check-shell` findings carry a `lint` field (e.g., `"S1"`, `"S11"`).
- `event` is set on `check-hook` findings when the finding is
  event-specific; `null` otherwise. `check-shell` findings always
  carry `event: null`.
- `line` is `null` for findings that are not line-scoped (most
  `check-hook` findings; some `check-shell` file-level findings).
- `external_tools` bubbles up the merged set from each inner
  `check-shell` call. When the same tool is absent across all inner
  calls, emit it once with a single `install_hint`.
- `findings` are ordered by severity (fail first), then by source
  (check-hook before check-shell for the same severity), then by hook
  path and line.

Zero-findings case: same envelope with `summary: {"fail": 0, "warn": 0, "total": 0}`
and `findings: []`.

## --as-tool contract

**Required fields:**

- `settings-path` — path to `.claude/settings.json` (or
  `.claude/settings.local.json`, or an explicit user-supplied settings
  file). No default under `--as-tool`; human mode retains the
  dual-path default behavior.

**Return shape:** DATA.

**Success** — JSON envelope with `value` carrying `settings_path`,
`summary`, `findings` (merged from `check-hook` and `check-shell`
sources; every entry carries `source`), and `external_tools` (bubbled
up from inner `check-shell` calls). See §5b for the full schema.

**NeedsMoreInfo** — JSON only: `missing: ["settings-path"]`, `hint:`
reminder that `settings-path` is the sole required field.

**Refusal** — JSON only: `reason:` one-sentence explanation;
`category:` one of `file-not-found` (settings path absent or
unreadable), `no-hooks` (file loaded but contains no `hooks:` key),
`parse-error` (settings JSON is malformed).

**Side effects:** reads the file at `settings-path`; scans `CLAUDE.md`
(if present) for rule-overlap detection; invokes
`/build:check-shell --as-tool path=<hook-script>` once per `"type":
"command"` hook script referenced by the settings file. Read-only on
the filesystem.

**Parallel-safe:** yes. Inner `check-shell` calls are parallel-safe;
concurrent outer calls on the same `settings-path` are redundant but
correct.

## Anti-Pattern Guards

1. **Treating rule overlap as always wrong** — hook + CLAUDE.md duplication can be intentional belt-and-suspenders; flag for user decision, don't recommend removal
2. **Skipping Primitive Routing when no hooks exist** — always scan CLAUDE.md for conversion signals even when there are no hooks; absence of hooks is itself a coverage gap worth surfacing
3. **Reading settings files from outside the current project** — only read `.claude/settings.json` and `.claude/settings.local.json` under the current project root unless the user provides an explicit path argument

## Key Instructions

- Under `--as-tool`: emit per the contract — a single JSON envelope
  with a `value` object carrying merged `findings` (each with a
  `source` field) and `external_tools`. No fenced blocks, no prose,
  no preamble.
- Under `--as-tool`: hard-fail with `NeedsMoreInfo` (JSON only) when
  `settings-path` is missing. Do not prompt — the caller will retry.
- `NeedsMoreInfo` and `Refusal` emit JSON only, never followed by
  fenced blocks.
- Every finding carries a `source` field — `"check-hook"` or
  `"check-shell"` — so callers can trace ownership across the
  delegation boundary.
- Read-only — do not modify any files; report findings only
- Always run Primitive Routing before numbered checks, even when no hooks are configured
- Stop hook loop risk (check 4) is a fail, not a warn — an unguarded blocking Stop hook creates an infinite loop that requires a session kill to recover

## Handoff

**Receives:** Settings file path (optional); reads `.claude/settings.json` and `.claude/settings.local.json` by default
**Produces:** Findings table per hook; read-only — no files modified
**Chainable to:** build-hook (to create or fix a hook based on findings)
