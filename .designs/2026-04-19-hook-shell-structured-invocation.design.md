---
name: Hook-Shell Structured Invocation
description: Hook and shell build/check pairs share a single source of truth by having the hook pair invoke the shell pair at runtime via an extended $ARGUMENTS contract with an --emit-only sentinel.
type: design
status: approved
related:
  - .plans/2026-04-19-build-check-shell-skill-pair.plan.md
  - .plans/2026-04-19-hook-shell-delegation.plan.md
---

# Hook-Shell Structured Invocation

## Purpose

Eliminate the duplication between `/build:build-hook` + `/build:check-hook`
and `/build:build-shell` + `/build:check-shell` by making the shell pair
the **runtime** source of truth for generic shell-script scaffolding and
the 14 FX lints. The hook pair invokes the shell pair mid-workflow with a
fully pre-filled intake and an `--emit-only` sentinel; the shell pair
produces structured output; the hook pair layers on hook-specific
content (stdin/JSON payload, `tool_input` extraction, `updatedInput`
contract, settings.json wiring, Stop-hook guards) and owns the single
user-facing Review Gate + Save.

Closes #327. Supersedes the reference-by-prose approach in
`.plans/2026-04-19-hook-shell-delegation.plan.md`.

## Why Now

- `/build:build-shell` + `/build:check-shell` just landed in build-0.4.0
  (commit `ae26fcb`), unblocking the delegation explicitly deferred
  during #322 scoping.
- The hook pair is the only primitive-pair in the repo today whose
  content meaningfully overlaps the shell pair. Cleaning this up
  establishes the pattern before #326 (Python-script pair) repeats it.
- Reference-by-prose delegation was scoped first (see
  `.plans/2026-04-19-hook-shell-delegation.plan.md`) and explicitly
  rejected in favor of a runtime contract that makes shell-pair
  improvements propagate automatically.

## Behavior

### The `$ARGUMENTS` contract

All four skills (`build-shell`, `check-shell`, and — for consistency —
`build-hook`, `check-hook`) accept `$ARGUMENTS` with the following
parsing rule:

| `$ARGUMENTS` shape | Mode | Behavior |
|---|---|---|
| empty | human, no prior context | full Elicit |
| freeform text (no `=` tokens, no `--` flags) | human, with seed intent | LLM parses what it can (purpose, target-shell hints, mentioned deps); Elicit for missing fields |
| contains one or more `key=value` tokens | human, structured | parse named fields; Elicit only for missing fields; non-kv tokens are ignored |
| `--emit-only` present | skill-caller | require all skill-specific required fields present; **hard-fail if any missing**; skip Elicit, Review Gate, Save, Test-handoff |

Mixed mode (freeform + kv) is disallowed to keep parsing deterministic.
If any `=` appears, all non-kv tokens are treated as noise.

Voice-dictated prompts fall naturally into the freeform-text row — e.g.,
`/build:build-shell I need a bash script that rotates nginx logs daily,
calls jq, should run on our macOS dev boxes` → LLM infers
`purpose=rotate nginx logs`, `deps=jq`, `target-shell=bash-3.2-portable`,
Elicit asks for invocation style + setuid + save path.

### `--emit-only` semantics

`--emit-only` = **"operate as a pure function: structured inputs in,
artifact out, no UI ceremony."**

| Workflow step | Standalone | `--emit-only` |
|---|---|---|
| Route | runs | runs |
| FX.1 Scope Gate (build-shell) / Tool Detection (check-shell) | runs | runs |
| Elicit | runs | **skipped**; hard-fail if any required field missing |
| Draft / Checks | runs | runs |
| Safety Check | runs; revises in place | runs; findings included in output |
| Review Gate | runs; waits for explicit approval | **skipped** — caller owns approval |
| Save | runs; writes file + `chmod +x` | **skipped** — caller writes |
| Test handoff | offers follow-up skill | **skipped** |

Output under `--emit-only` is **structured** — not a chat-rendered
table, not a prose report. The caller consumes and renders.

Required fields for `build-shell --emit-only`:
`target-shell`, `purpose`, `invocation-style`, `setuid`, `deps`,
`save-path` (informational only — caller owns the write).

Required fields for `check-shell --emit-only`:
`script-path` (or `script-content` for inline scripts not yet on disk).

### Structured output shape

**build-shell --emit-only** returns:

- `scaffold` — the scaffold string (the script as it would be written)
- `fx1_refusal` — optional: populated if FX.1 fires, contains the
  signal name and recommendation copy; caller decides whether to
  propagate
- `safety_findings` — zero or more `{severity, check, finding, line}`
  entries from the in-skill Safety Check

**check-shell --emit-only** returns:

- `missing_tools` — zero or more `{tool, install_cmd, coverage_gap}`
  entries (feeds the caller's Missing Tools preamble)
- `findings` — normalized rows: `{severity, group, lint, finding, line}`
- `tool_output` — optional: raw output from `shellcheck` / `shfmt` /
  `checkbashisms` if any ran, keyed by tool name

### Check-shell's hook-script refusal under `--emit-only`

check-shell today refuses to audit hook scripts (routes to
`/build:check-hook`). Under `--emit-only`, this refusal is bypassed —
the caller has explicitly taken responsibility. Direct human invocation
of `/build:check-shell .claude/hooks/foo.sh` still routes away to
check-hook, preserving the UX courtesy.

### build-hook's new Draft flow

1. Human Elicit (hook event, handler type, enforcement goal) — unchanged.
2. **Derive shell-pair intake** from hook context:
   - `target-shell`: `bash-3.2-portable` (default; Claude Code hooks run
     under the user's `/bin/bash`, which is 3.2 on macOS).
   - `invocation-style`: `glue` (hooks are one-shot, no flags).
   - `setuid`: `no` (hooks never run setuid).
   - `deps`: inferred from the enforcement goal (commonly `jq`; may
     include `curl`, `grep`, etc.).
   - `purpose`: the hook's enforcement goal, one sentence.
   - `save-path`: `.claude/hooks/<name>.sh`.
3. **Invoke** `/build:build-shell` with those six fields + `--emit-only`.
4. Receive `scaffold` string. If `fx1_refusal` is populated, halt and
   propagate the FX.1 recommendation to the user — a hook too complex
   for shell is a real signal to switch to a Python handler or agent
   handler.
5. Layer hook-specific content onto the scaffold: `INPUT=$(cat)`
   immediately after strict-mode preamble, the `tool_input` jq
   extraction table as prose, the `updatedInput` JSON output contract,
   the settings.json entry block.
6. Present **one unified Review Gate** — the complete hook script +
   settings.json snippet. No second gate.
7. On approval, **one Save** — write to `.claude/hooks/<name>.sh`,
   `chmod +x`, show settings.json patch.

### check-hook's new audit flow

1. Input (settings file path) — unchanged.
2. Primitive Routing — unchanged (scans CLAUDE.md for conversion signals).
3. For each hook script the audit covers:
   - **Invoke** `/build:check-shell script-path=<path> --emit-only`.
   - Receive `findings`, `missing_tools`, `tool_output`.
4. Run hook-specific checks (stdin correctness, matcher casing, Stop
   hook loop, jq field-path correctness, `tool_input` vs `toolArgs`
   on Copilot, CVE-2025-59536 `settings.json` attack surface, etc.).
5. **Merge findings** into one unified table with columns:
   `severity | source | check | finding | location`.
   `source` is either `FX` (from check-shell) or `hook` (from check-hook).
   Missing Tools preamble sits at the top of the report as a block,
   outside the table.
6. Report.

## Components

### Four SKILL.md files

- `plugins/build/skills/build-shell/SKILL.md` — extend argument parser,
  add `--emit-only` branch, factor Review Gate / Save into conditional
  steps.
- `plugins/build/skills/check-shell/SKILL.md` — add `--emit-only`
  branch, document structured output shape, bypass hook-script refusal
  when `--emit-only` is set.
- `plugins/build/skills/build-hook/SKILL.md` — replace inline generic
  script scaffolding (lines ~74-85, 117-133) with a **Derive Shell
  Intake** step + build-shell invocation; collapse Safety Check item #8
  into the invocation contract.
- `plugins/build/skills/check-hook/SKILL.md` — invoke check-shell
  `--emit-only` per hook script; delete checks 11, 12 (unquoted
  portion), 14, 15 (a/b/d); renumber remaining; add unified-report
  rendering section.

### One shared reference file

`plugins/build/_shared/references/shell-argument-contract.md` —
**single authoritative source** for:
- The `$ARGUMENTS` parsing rule table.
- `--emit-only` semantics (skip-or-run-per-step table).
- Required-fields list per skill.
- Structured output shape per skill.
- Bypass rules (e.g., check-shell hook-script refusal).

All four SKILL.md files reference this file. Changes to the contract
edit one file, not four.

### Version bump

Build plugin `0.4.0` → `0.5.0` (minor — behavioral change to existing
skills across the pair). Updates:
- `plugins/build/pyproject.toml`
- `plugins/build/.claude-plugin/plugin.json`

## Constraints

### Must have

- `--emit-only` hard-fails on missing required fields (no silent
  fallback to interactive Elicit — callers must be explicit).
- FX.1 scope gate still fires under `--emit-only`; the caller
  (build-hook) receives the refusal structured and propagates to the
  user. A hook that triggers FX.1 is a signal to switch to a Python
  handler; this routing must not be silenced.
- check-shell's 14 FX lints remain the single source of truth — not
  mirrored, not forked, not partially duplicated inside check-hook.
- check-hook retains hook-specific checks verbatim: stdin correctness,
  matcher casing, path expansion, Stop hook loop, jq field-path
  correctness, `updatedInput` parallel hooks, `toolArgs` Copilot
  divergence, CVE-2025-59536, PostToolUse-can't-block, async+blocking
  contradiction, latency, idempotency, rule overlap.
- build-hook retains hook-specific Draft content verbatim:
  `INPUT=$(cat)`, `tool_input` jq table, `updatedInput` JSON contract,
  settings.json entry block, Stop Hook Guard section, Security Note,
  Known Limitations, recursive-loop safety.
- Single unified Review Gate in build-hook. Single merged report in
  check-hook.
- All four SKILL.md files pass `/build:check-skill` with zero
  fail-level findings after the refactor.
- Freeform-text `$ARGUMENTS` (voice-dictated intent, no `=`, no `--`)
  still works for human invocations of all four skills.

### Won't have

- `--called-by=<skill>` metadata. YAGNI — `--emit-only` alone carries
  the semantics needed today. A future second caller can motivate the
  addition.
- Mixed freeform + kv parsing. If any `=` appears, all non-kv tokens
  are noise.
- New lints in check-shell to close "missing strict-mode preamble as a
  standalone lint" gaps that exist only inside check-hook. Those hook-
  specific preamble expectations stay in check-hook.
- Refactor of `/build:build-rule`, `/build:build-subagent`,
  `/build:build-skill`, or other primitives. The pattern established
  here is available for #326 (Python-script pair) to adopt, not a
  mandate for everything.
- `.claude-plugin/marketplace.json` changes (manifest references
  plugins, not skills).
- A programmatic test harness for the argument-parser contract.
  Validation is by manual invocation + self-audit with
  `/build:check-skill`.
- Windows / PowerShell support — FX.1 still refuses at intake.
- Skills written to disk before Review Gate passes (build-hook's
  existing safety requirement is preserved through the single unified
  gate).

## Acceptance Criteria

Verifiable from outside:

1. **`--emit-only` is a real code path.** Invoke `/build:build-shell
   target=bash-3.2-portable purpose="test" invocation=glue setuid=no
   deps=jq save-path=/tmp/x.sh --emit-only`. Skill produces the
   scaffold as output without asking any question and without writing
   any file.

2. **Missing required fields under `--emit-only` hard-fails.** Invoke
   `/build:build-shell target=bash-3.2-portable --emit-only`. Skill
   exits with a clear error naming the missing fields. Does not prompt
   interactively.

3. **Freeform-text intake still works.** `/build:build-shell rotate
   nginx logs daily using jq on macOS` → skill infers what it can and
   asks only for the remaining fields. No crash, no silent drop.

4. **FX.1 under `--emit-only` propagates.** Invoke with an intake that
   triggers FX.1 (e.g., `purpose="concurrent task orchestration"`). Skill
   returns `fx1_refusal` populated in structured output rather than
   halting interactively.

5. **build-hook Draft flow is single-gate.** A full run of
   `/build:build-hook PreToolUse "block rm -rf"` produces one combined
   Review Gate (hook script + settings.json snippet), not two.

6. **No double-intake.** During the build-hook flow, the user is asked
   at most three hook-specific questions (event, handler type, goal).
   No question that build-shell would ask in standalone mode appears.

7. **check-hook produces a unified report.** A full run of
   `/build:check-hook` on a project with a hook script produces a
   single findings table with the `source` column populated as `FX` or
   `hook`. Missing Tools preamble appears once, at the top.

8. **Shell-pair SKILL.md content that moves out of hook-pair SKILL.md
   doesn't reappear verbatim anywhere.** Grep test:
   `grep -c "lower_case_with_underscores\|UPPER_CASE_WITH_UNDERSCORES"
   plugins/build/skills/build-hook/SKILL.md` returns 0.
   `grep -c "shellcheck\|shfmt"
   plugins/build/skills/check-hook/SKILL.md` returns 0 outside the
   delegation pointer.

9. **Hook-specific content survives.** Every one of these tokens still
   appears in post-refactor check-hook SKILL.md:
   `INPUT=$(cat)`, `tool_input`, `stop_hook_active`, `updatedInput`,
   `CVE-2025-59536`, `PostToolUse`, `toolArgs`, `permissionDecision`.

10. **Argument contract lives in one place.**
    `plugins/build/_shared/references/shell-argument-contract.md`
    exists and is referenced by all four SKILL.md files (in their
    `references:` frontmatter).

11. **Check-skill self-audit is clean.** `/build:check-skill` on each of
    the four SKILL.md files shows zero fail-level findings.

12. **Version bump is coherent.**
    `plugins/build/pyproject.toml` and
    `plugins/build/.claude-plugin/plugin.json` both show `0.5.0`.

## Open Questions

None blocking. All four decisions locked during scoping:
- Mechanism: structured runtime invocation via extended `$ARGUMENTS`.
- Payload shape: `key=value` pairs with freeform-intent fallback.
- Sentinel: `--emit-only` only (no `--called-by`).
- Merge shape: one unified table with `source` column.
