---
name: Hook-Shell Structured Invocation
description: Implement runtime delegation from the hook pair to the shell pair via extended $ARGUMENTS parsing and an --emit-only sentinel, with a shared contract file as the single source of truth.
type: plan
status: draft
branch: feat/327-hook-shell-structured-invocation
related:
  - .designs/2026-04-19-hook-shell-structured-invocation.design.md
  - .plans/2026-04-19-hook-shell-delegation.plan.md
---

# Hook-Shell Structured Invocation

## Goal

Ship runtime delegation between the hook and shell build/check pairs.
After this plan lands:

- `/build:build-shell` and `/build:check-shell` accept `$ARGUMENTS` with
  four parsing modes (empty, freeform, `key=value`, `--emit-only`).
- Under `--emit-only`, both shell skills run their computation (scope
  gate / checks / safety) but skip Elicit, Review Gate, Save, and
  Test handoff, returning structured output instead.
- `/build:build-hook` derives shell-pair intake from hook context,
  invokes `/build:build-shell --emit-only`, layers hook-specific content,
  and owns one unified Review Gate + Save.
- `/build:check-hook` invokes `/build:check-shell --emit-only` per hook
  script and merges findings into a single unified table with a
  `source` column.
- All four SKILLs reference one shared contract file
  (`plugins/build/_shared/references/emit-only-contract.md`).
- Build plugin bumps to `0.5.0`.

Closes #327. Supersedes `.plans/2026-04-19-hook-shell-delegation.plan.md`.

## Scope

### Must have

- `plugins/build/_shared/references/emit-only-contract.md` —
  **generic** pattern spec covering the `$ARGUMENTS` parsing rule,
  `--emit-only` skip/run-per-step semantics, and structured-output
  conventions. Skill-agnostic — no shell-specific field lists. Any
  future invocable skill (in any plugin) references this file as the
  authoritative mechanism. Per-skill specifics (required fields,
  output shapes, bypass rules) live **inline** in each invocable
  skill's own SKILL.md, not in this contract file.
- `plugins/build/skills/build-shell/SKILL.md` — refactored so §3 Elicit
  encodes the four-mode parsing rule, `--emit-only` skips Elicit /
  Review Gate / Save, FX.1 still runs and returns a structured refusal
  when fired under `--emit-only`, references the shared contract in
  frontmatter.
- `plugins/build/skills/check-shell/SKILL.md` — refactored so input
  parsing accepts `--emit-only`, the hook-script refusal in §1 Input
  is bypassed when the flag is present, structured output shape
  (`missing_tools`, `findings`, `tool_output`) is documented,
  references the shared contract.
- `plugins/build/skills/build-hook/SKILL.md` — §3 Draft replaced with
  (a) human Elicit for hook-specific fields, (b) Derive Shell Intake
  step that maps hook context to the six shell-pair fields,
  (c) invocation of `/build:build-shell --emit-only`, (d) layering
  step for hook-specific script content (`INPUT=$(cat)`, jq
  extraction, `updatedInput` JSON contract, settings.json entry),
  (e) one unified Review Gate, (f) one Save. Safety Check item #8
  (ShellCheck + shfmt) removed in favor of the delegation contract.
  Hook-specific content preserved verbatim: Security Note, Stop Hook
  Guard, Known Limitations, all hook-specific Safety Check items
  (stdin correctness, matcher casing, jq availability, `updatedInput`
  parallelism, latency, recursive-loop safety).
- `plugins/build/skills/check-hook/SKILL.md` — §4 Checks restructured
  so each hook script's audit invokes `/build:check-shell --emit-only`,
  receives structured findings, and merges them into a unified table
  with columns `severity | source | check | finding | location`.
  `source ∈ {FX, hook}`. Missing Tools preamble sits at top of report
  as a block. Delegable checks removed: #14 ShellCheck static analysis
  (fully delegated); the unquoted-variable portion of #12 Injection
  safety (delegated to FX S1; `eval`-on-payload stays); parts (a/b/d)
  of #15 Script style (delegated to FX D6 / P1). Hook-specific checks
  preserved verbatim: #1 PreToolUse gap, #3 Async+blocking, #4 Stop
  hook loop, #5 Stdin correctness, #6 Matcher casing + path expansion,
  #7 PostToolUse enforcement intent, #8 Rule overlap, #9 Idempotency,
  #10 Latency, #11 Script safety preamble (hook-specific framing
  stays — the check-shell catalog does not have a direct delegate),
  #13 jq availability + field-path correctness, #15 (c) `set -x`
  payload-leak, #16 settings.json attack surface.
- `plugins/build/pyproject.toml` and
  `plugins/build/.claude-plugin/plugin.json` version
  `0.4.0` → `0.5.0`.
- `.plans/2026-04-19-hook-shell-delegation.plan.md` marked
  `status: superseded` with a link to this plan.
- All four SKILL.md files pass `/build:check-skill` with zero
  fail-level findings.
- PR opened against `main` referencing `#327`, with CI green (ruff).

### Won't have

- `--called-by=<skill>` metadata. YAGNI — `--emit-only` alone carries
  the semantics. A future second caller motivates the addition.
- Mixed freeform + kv parsing. If any `=` appears in `$ARGUMENTS`, all
  non-kv tokens are noise.
- New lints in check-shell (e.g., an explicit "missing strict-mode
  preamble" lint) to close asymmetries that currently exist only in
  check-hook. Those hook-specific preamble expectations stay in
  check-hook (#11).
- Refactor of `/build:build-rule`, `/build:build-subagent`,
  `/build:build-skill`, `/build:refine-prompt`, or other primitives.
  The pattern established here is available for #326 (Python-script
  pair) to adopt voluntarily; it is not a mandate.
- Automated integration tests of the slash-command flows. Skills are
  LLM-interpreted; acceptance is manual invocation + self-audit with
  `/build:check-skill`.
- A programmatic parser test for the argument-contract grammar.
- `.claude-plugin/marketplace.json` changes (manifest references the
  plugin, not individual skills).
- Windows / PowerShell support. FX.1 still refuses at intake.
- Changes to `plugins/build/skills/build-hook/references/hook-testing.md`
  or `plugins/build/skills/check-hook/references/platform-limitations.md`.
  Already hook-specific; no overlap with shell pair.

## Approach

**Bottom-up order.** Write the shared contract file first, then extend
the shell pair (which consumes the contract), then refactor the hook
pair (which invokes the shell pair). This keeps each task verifiable
standalone: the contract is a document, the shell-pair refactor can be
exercised by manual `--emit-only` invocation before any hook-pair work,
and the hook-pair refactor depends on observable shell-pair behavior,
not speculated behavior.

**Delegation mechanic.** When the hook skill needs to invoke the shell
skill at runtime, its SKILL.md prose instructs the executing LLM to use
the Skill tool to invoke the counterpart skill with a pre-filled
`$ARGUMENTS` payload. The shell skill's SKILL.md handles `--emit-only`
as a first-class parsing branch. Claude Code's Skill tool supports this
chain today — this is net-new within toolkit but not a net-new Claude
Code feature.

**Preserve hook-pair UX.** The single-skill user experience for
`/build:build-hook` and `/build:check-hook` must not regress. Users see
the hook-pair's prompts and the hook-pair's output; the internal
invocation of the shell pair is silent from their perspective. Concrete
contract: no question that build-shell would have asked in standalone
mode appears during a build-hook run; check-hook produces one merged
report, not two.

**Preserve FX.1 signal.** An FX.1 scope-gate refusal inside a build-hook
run is high-value information — the hook is too complex for shell and
should be a Python or agent handler. The shell skill's `--emit-only`
path returns the refusal structured; build-hook propagates the
recommendation to the user and halts. This is the design's one "fail
loud" path through the delegation.

**Supersede vs. delete the prior plan.** The reference-by-prose plan at
`.plans/2026-04-19-hook-shell-delegation.plan.md` is marked
`status: superseded` with a link forward. Keeping it preserves the
reasoning trail for why the runtime-invocation approach was chosen over
the simpler reference-only approach.

**Self-audit is the quality gate.** After each SKILL.md edit, the
`/build:check-skill` run serves as the acceptance test. Any fail-level
finding blocks the task's commit until resolved.

## File Changes

| File | Change |
|------|--------|
| `plugins/build/_shared/references/emit-only-contract.md` | **Create** — generic mechanism spec: `$ARGUMENTS` parsing rule, `--emit-only` skip/run-per-step semantics, structured-output conventions. Skill-agnostic. |
| `plugins/build/skills/build-shell/SKILL.md` | **Modify** — extend argument parser, add `--emit-only` branch to Elicit / Review Gate / Save, document FX.1 structured-refusal return, add contract reference to frontmatter. |
| `plugins/build/skills/check-shell/SKILL.md` | **Modify** — extend input parsing, add `--emit-only` branch that bypasses hook-script refusal and returns structured output, document output shape, add contract reference to frontmatter. |
| `plugins/build/skills/build-hook/SKILL.md` | **Modify** — §3 Draft restructured: hook-specific Elicit → Derive Shell Intake → invoke build-shell `--emit-only` → layer hook-specific content → single Review Gate + Save. Delete Safety Check #8. Preserve all hook-specific content. |
| `plugins/build/skills/check-hook/SKILL.md` | **Modify** — §4 Checks restructured: per-hook invocation of check-shell `--emit-only`, merge into unified table with `source` column. Delete checks #14 and delegable portions of #12 / #15. Renumber. |
| `plugins/build/pyproject.toml` | **Modify** — version `0.4.0` → `0.5.0`. |
| `plugins/build/.claude-plugin/plugin.json` | **Modify** — version `0.4.0` → `0.5.0`. |
| `.plans/2026-04-19-hook-shell-delegation.plan.md` | **Modify** — `status: draft` → `status: superseded`; add `superseded_by:` link in frontmatter. |

No deletions of existing files. No new reference files beyond the one
shared contract.

## Tasks

### Chunk 1: Shared contract

#### Task 1: Write the generic emit-only contract

Create `plugins/build/_shared/references/emit-only-contract.md`.
**Skill-agnostic** — this file describes the mechanism, not any
particular skill's inputs/outputs. Per-skill required fields and
output shapes live inline in each invocable skill's own SKILL.md.

Contents:
- Frontmatter: name, description, type (reference).
- Section: **Purpose** — one paragraph: runtime pattern for one skill
  to invoke another as a pure function via `$ARGUMENTS` + a sentinel
  flag; the caller owns gating and side effects.
- Section: **Parsing rule** — the four-mode table (empty / freeform /
  `key=value` / `--emit-only`) as specified in the design.
- Section: **`--emit-only` semantics** — generic skip/run-per-step
  table: Elicit (skipped), Review Gate (skipped), Save (skipped),
  Test handoff (skipped); domain-specific computation steps (Route,
  Draft, Checks, Safety) still run.
- Section: **Required-fields contract** — invocable skills **must**
  document their required-fields list inline in their SKILL.md;
  missing required fields under `--emit-only` **must** hard-fail
  (no silent fallback to Elicit).
- Section: **Structured output conventions** — invocable skills return
  a structured object (JSON-shaped) whose schema is documented inline
  in the skill's SKILL.md. Convention: include a field for primary
  artifact, an array for findings/warnings, and an optional field for
  refusal conditions (e.g., scope-gate fires that a human-UX version
  would halt on).
- Section: **When to use this pattern** — when a skill's computation is
  reusable by another skill, and the consuming skill can pre-fill all
  required inputs. Not for cases where the user must participate in
  the inner skill's decisions.
- Section: **When NOT to use** — one-off reuse (prefer reference-by-prose),
  user-facing inner skills whose intake is judgment-heavy (pre-filling
  defeats the purpose), or chains where skills compose sequentially
  (use a `*.chain.md` manifest + `/build:check-skill-chain` instead).
- Section: **Freeform-text mode** — voice-dictated intent is a
  first-class human input shape; the consuming skill's LLM parses it.
  Does not apply under `--emit-only`.

**Verify:**
```
test -f plugins/build/_shared/references/emit-only-contract.md && \
  grep -c "^## " plugins/build/_shared/references/emit-only-contract.md
```
Second command returns ≥ 7 (seven or more top-level sections).

**Commit:** `docs(build): add emit-only-contract shared reference`

#### Task 2: Mark prior plan superseded

Edit `.plans/2026-04-19-hook-shell-delegation.plan.md`: change
`status: draft` to `status: superseded`; add
`superseded_by: .plans/2026-04-19-hook-shell-structured-invocation.plan.md`
in frontmatter.

**Verify:**
```
grep "^status:" .plans/2026-04-19-hook-shell-delegation.plan.md
grep "^superseded_by:" .plans/2026-04-19-hook-shell-delegation.plan.md
```
Both return one line; first says `superseded`; second points at this plan.

**Commit:** `docs(plans): supersede reference-by-prose plan with structured-invocation plan`

### Chunk 2: Shell pair — emit-only branch

#### Task 3: Refactor build-shell SKILL.md

Modify `plugins/build/skills/build-shell/SKILL.md`:

- Add `../../_shared/references/emit-only-contract.md` to
  frontmatter `references:`.
- Rewrite §3 Elicit opening paragraph to reference the four-mode
  parsing rule from the contract. Keep the six intake questions
  verbatim — they become the "fields elicited when not pre-filled"
  list.
- Add a new step before Elicit (or folded into Elicit's opening)
  titled **`--emit-only` branch**: when `--emit-only` is in
  `$ARGUMENTS`, validate that all six required fields are present;
  hard-fail with a clear error naming missing fields; otherwise skip
  directly to §4 Draft.
- Modify §2 FX.1 Scope Gate: under `--emit-only`, if a signal fires,
  return a structured `fx1_refusal` in the emit output (signal name +
  recommendation copy) instead of halting interactively.
- Modify §5 Safety Check: under `--emit-only`, findings are appended
  to the emit output as `safety_findings` rather than causing
  in-chat revision.
- Modify §6 Review Gate: condition the entire step on "not
  `--emit-only`." Under `--emit-only`, skip.
- Modify §7 Save: same — skip entirely under `--emit-only`.
- Modify §8 Test: skip under `--emit-only`.
- Update the "Workflow sequence" line at the top to indicate
  conditional steps.
- Add one paragraph at the end of §3 Elicit (or in a new "Output under
  emit-only" subsection) summarizing the structured output shape
  (`{scaffold, fx1_refusal?, safety_findings[]}`).

**Verify:**
```
grep -c "emit-only" plugins/build/skills/build-shell/SKILL.md
```
Returns ≥ 4 (opening, Elicit branch, Review Gate skip, Save skip — at minimum).

```
grep "emit-only-contract" plugins/build/skills/build-shell/SKILL.md
```
Returns at least one line (the frontmatter reference).

Manual smoke: a new-session agent can read the refactored SKILL.md and
explain the `--emit-only` path without additional context.

**Commit:** `feat(build-shell): add --emit-only branch and shared contract reference`

#### Task 4: Refactor check-shell SKILL.md

Modify `plugins/build/skills/check-shell/SKILL.md`:

- Add `../../_shared/references/emit-only-contract.md` to
  frontmatter `references:`.
- Modify §1 Input: accept `--emit-only` in `$ARGUMENTS`; require
  `script-path` or `script-content` pre-filled; document the four-mode
  parsing rule by reference to the contract.
- Modify §1 Input's hook-script refusal (currently in the opening
  paragraph that routes hook scripts to `/build:check-hook`): lift the
  refusal when `--emit-only` is set. Keep the refusal for direct human
  invocation.
- Modify §3 Missing Tools Preamble: under `--emit-only`, return
  `missing_tools` as structured entries in the emit output rather than
  rendering a preamble block.
- Modify §4 Checks: under `--emit-only`, findings are returned as
  normalized rows in the emit output (`{severity, group, lint,
  finding, line}`) rather than rendered into the report table.
- Modify §5 Report: condition the entire step on "not `--emit-only`".
  Under `--emit-only`, the skill returns the structured output and stops.
- Modify §6 Handoff: skip under `--emit-only`.
- Add one paragraph summarizing structured output shape:
  `{missing_tools[], findings[], tool_output{}}`.

**Verify:**
```
grep -c "emit-only" plugins/build/skills/check-shell/SKILL.md
```
Returns ≥ 4.

```
grep "emit-only-contract" plugins/build/skills/check-shell/SKILL.md
```
Returns at least one line.

Manual smoke: a new-session agent can read the refactored SKILL.md and
explain how check-shell under `--emit-only` handles a hook script path
without hitting the refusal.

**Commit:** `feat(check-shell): add --emit-only branch and lift hook-script refusal`

### Chunk 3: Hook pair — runtime invocation

#### Task 5: Refactor build-hook SKILL.md

Modify `plugins/build/skills/build-hook/SKILL.md`:

- Add `../../_shared/references/emit-only-contract.md` to
  frontmatter `references:`.
- Keep §1 Route and §2 Elicit verbatim (hook-specific intake: event,
  handler type, enforcement goal).
- Replace §3 Draft entirely. New structure:
  - **§3a Derive Shell Intake.** Map hook context to the six
    shell-pair fields with defaults:
    - `target-shell`: `bash-3.2-portable` (macOS `/bin/bash` is 3.2)
    - `invocation-style`: `glue`
    - `setuid`: `no`
    - `deps`: inferred from enforcement goal (default `[jq]`); may
      include `curl`, `grep`, `git`, etc.
    - `purpose`: the enforcement goal (one sentence)
    - `save-path`: `.claude/hooks/<name>.sh`
  - **§3b Invoke build-shell.** Construct `$ARGUMENTS` string
    (`target=bash-3.2-portable purpose="<goal>" invocation=glue
    setuid=no deps=jq save-path=.claude/hooks/<name>.sh --emit-only`),
    invoke `/build:build-shell`, receive structured output.
  - **§3c Propagate FX.1 if fired.** If `fx1_refusal` is populated in
    the emit output, halt and surface the signal + recommendation to
    the user. Do not proceed to layering.
  - **§3d Layer hook-specific content** onto `scaffold`: insert
    `INPUT=$(cat)` immediately after the strict-mode preamble; append
    the `tool_input` jq path table as guidance (kept verbatim from
    current SKILL.md); append the `updatedInput` / broader JSON
    output contract section (kept verbatim); produce the settings.json
    entry block (kept verbatim).
- Delete Safety Check item #8 (ShellCheck + shfmt) — delegated. Keep
  items #1–#7, #9–#11 (hook-specific).
- Keep §5 Stop Hook Guard, Security Note, Known Limitations, §6 Rule
  Overlap verbatim.
- Consolidate §7 Review Gate and §8 Save: one gate, one save, for the
  combined hook script + settings.json snippet. Language updated to
  say "this gate covers both the scaffolded body from build-shell and
  the hook-specific additions."
- Keep §9 Test verbatim (offers `/build:check-hook`).

**Verify:**
```
grep -c "emit-only" plugins/build/skills/build-hook/SKILL.md
```
Returns ≥ 2 (invocation step + contract reference).

Hook-specific content survives:
```
for token in "INPUT=\$(cat)" "tool_input" "updatedInput" "stop_hook_active" \
             "CVE-2025-59536" "PostToolUse" "permissionDecision"; do
  grep -q "$token" plugins/build/skills/build-hook/SKILL.md || echo "MISSING: $token"
done
```
Prints nothing (all tokens present).

Generic content removed:
```
grep -c "lower_case_with_underscores\|UPPER_CASE_WITH_UNDERSCORES" \
  plugins/build/skills/build-hook/SKILL.md
```
Returns 0.

**Commit:** `feat(build-hook): delegate script scaffolding to build-shell via --emit-only invocation`

#### Task 6: Refactor check-hook SKILL.md

Modify `plugins/build/skills/check-hook/SKILL.md`:

- Add `../../_shared/references/emit-only-contract.md` to
  frontmatter `references:`.
- Keep §1 Input, §2 Primitive Routing, §3 Platform Scope verbatim.
- Restructure §4 Checks:
  - Insert a new step **§4a Invoke check-shell per hook script.** For
    each `command`-type hook, invoke `/build:check-shell
    script-path=<path> --emit-only`, receive structured
    `{missing_tools, findings, tool_output}`.
  - **§4b Hook-specific checks.** Renumbered hook-only checks in the
    existing prose style:
    1. PreToolUse gap (current #1)
    2. Async + blocking contradiction (current #3)
    3. Stop hook loop (current #4)
    4. Stdin correctness (current #5)
    5. Matcher casing + path expansion (current #6)
    6. PostToolUse enforcement intent (current #7)
    7. Rule overlap (current #8)
    8. Idempotency (current #9)
    9. Latency (current #10)
    10. Hook-specific script safety preamble (current #11, kept —
        check-shell has no direct delegate for this, explicitly
        documented in the Won't-have)
    11. `eval` on payload-derived value (pulled from current #12;
        unquoted-variable portion deleted — delegated)
    12. jq availability + field-path correctness (current #13)
    13. Hook-specific style: `set -x` payload-leak (from current #15
        (c); parts (a), (b), (d) deleted — delegated)
    14. `settings.json` attack surface (current #16)
  - Delete current check #14 ShellCheck static analysis entirely
    (fully delegated).
  - Update the opening line of §4 to reflect the new count.
- Modify §5 Report: render one **unified table** with columns
  `severity | source | check | finding | location`. `source` is
  either `FX` (from check-shell) or `hook`. Missing Tools preamble
  from check-shell sits at top of report as a block, above the table.
- Keep Anti-Pattern Guards and Key Instructions; update the
  "Run sixteen checks" count if it appears.

**Verify:**
```
grep -c "emit-only" plugins/build/skills/check-hook/SKILL.md
```
Returns ≥ 2.

Generic lints removed:
```
grep -c "shellcheck" plugins/build/skills/check-hook/SKILL.md
```
Returns ≤ 1 (at most one reference, in the delegation block or
hook-specific context).

Hook-specific content survives:
```
for token in "INPUT=\$(cat)" "tool_input" "stop_hook_active" "updatedInput" \
             "CVE-2025-59536" "PostToolUse" "toolArgs" "permissionDecision"; do
  grep -q "$token" plugins/build/skills/check-hook/SKILL.md || echo "MISSING: $token"
done
```
Prints nothing.

Unified table schema is documented:
```
grep "severity.*source.*check.*finding" plugins/build/skills/check-hook/SKILL.md
```
Returns at least one line (the column header in the §5 Report example).

**Commit:** `feat(check-hook): invoke check-shell --emit-only and merge findings into unified table`

### Chunk 4: Release

#### Task 7: Self-audit with check-skill

Run `/build:check-skill` on each of the four SKILL.md files:
- `plugins/build/skills/build-shell/SKILL.md`
- `plugins/build/skills/check-shell/SKILL.md`
- `plugins/build/skills/build-hook/SKILL.md`
- `plugins/build/skills/check-hook/SKILL.md`

For any fail-level finding, fix in the corresponding SKILL.md and
re-audit. Warns acceptable if they existed pre-refactor or are
explicitly documented in the file's Key Instructions.

**Verify:** Zero fail-level findings across all four files.

**Commit:** None if no edits needed. If fixes were made, commit:
`fix(build): resolve check-skill findings from hook-shell delegation refactor`

#### Task 8: Bump build plugin version

Edit `plugins/build/pyproject.toml`: `version = "0.4.0"` →
`version = "0.5.0"`.

Edit `plugins/build/.claude-plugin/plugin.json`: `"version": "0.4.0"` →
`"version": "0.5.0"`.

**Verify:**
```
grep version plugins/build/pyproject.toml \
             plugins/build/.claude-plugin/plugin.json
```
Both lines show `0.5.0`.

**Commit:** `chore(build): bump to 0.5.0 for hook-shell structured invocation`

#### Task 9: Open PR for #327

Push the branch and open a PR against `main` with:
- Title: `feat(build): hook pair delegates to shell pair via --emit-only (build-0.5.0)`
- Body: Summary bullets (contract file, four SKILL.md refactors,
  version bump, supersedes prior plan). Test plan: manual invocation
  of `/build:build-hook` and `/build:check-hook` to confirm single
  gate / single report. Link to issue `#327` and the design doc.

**Verify:** `gh pr view` returns the PR URL; CI (ruff) is green.

**Commit:** None (PR creation is not a commit).

#### Task 10: Open follow-up issue for `/build:build-skill` pattern awareness

Open a new GitHub issue (not this PR) titled:
`/build:build-skill — add "make this skill invocable" option (emit-only pattern)`

Body:
- **Context:** The emit-only invocation pattern was introduced in
  `#327` (see `plugins/build/_shared/references/emit-only-contract.md`).
  `/build:build-skill` currently scaffolds skills without awareness of
  the pattern — authors who want their skill to be invocable by
  another skill have to retrofit the `--emit-only` branch manually.
- **Goal:** Offer "should this skill be invocable by other skills?"
  as part of `/build:build-skill`'s intake; when yes, scaffold the
  `$ARGUMENTS` parsing branch, the skip/run conditionals on Elicit /
  Review Gate / Save, the structured-output shape, and a reference to
  the shared contract in the new skill's frontmatter.
- **Related:** `#327`, `plugins/build/_shared/references/emit-only-contract.md`,
  `.designs/2026-04-19-hook-shell-structured-invocation.design.md`.

**Verify:** `gh issue view <new-issue-number>` returns the issue URL.

**Commit:** None (issue creation is not a commit).

## Validation

After all tasks complete, the following must all hold:

1. **Shared contract exists.** `test -f
   plugins/build/_shared/references/emit-only-contract.md` and
   `grep -c "^## " plugins/build/_shared/references/emit-only-contract.md`
   returns ≥ 6 (six or more top-level sections).

2. **All four SKILLs reference the shared contract.** `grep -l
   "emit-only-contract" plugins/build/skills/{build,check}-{shell,hook}/SKILL.md`
   returns four file paths.

3. **`--emit-only` is documented in all four SKILLs.** `grep -l
   "emit-only" plugins/build/skills/{build,check}-{shell,hook}/SKILL.md`
   returns four file paths.

4. **Generic scaffold prose is absent from build-hook.** `grep -c
   "lower_case_with_underscores\|UPPER_CASE_WITH_UNDERSCORES"
   plugins/build/skills/build-hook/SKILL.md` returns 0.

5. **ShellCheck/shfmt prose is absent from check-hook outside
   delegation.** `grep -c "shellcheck\|shfmt"
   plugins/build/skills/check-hook/SKILL.md` returns ≤ 2 (one in the
   invocation step, one in the hook-specific preamble framing — no
   more).

6. **Hook-specific content survives in both hook SKILLs.** For each
   token in `{INPUT=$(cat), tool_input, stop_hook_active,
   updatedInput, CVE-2025-59536, PostToolUse, toolArgs (check-hook
   only), permissionDecision}`, `grep -q "$token"` succeeds against
   the relevant file.

7. **Unified-table schema is documented in check-hook.** `grep
   "severity.*source.*check.*finding"
   plugins/build/skills/check-hook/SKILL.md` returns at least one line.

8. **Prior plan is superseded.** `grep "^status:"
   .plans/2026-04-19-hook-shell-delegation.plan.md` outputs
   `status: superseded`; `grep "^superseded_by:"` points at this plan.

9. **Version bump is coherent.** `grep version
   plugins/build/pyproject.toml
   plugins/build/.claude-plugin/plugin.json` shows `0.5.0` on both.

10. **check-skill self-audit is clean.** Running `/build:check-skill`
    against each of the four SKILL.md files produces zero fail-level
    findings.

11. **Manual smoke — build-hook single-gate.** `/build:build-hook
    PreToolUse "block rm -rf"` produces one combined Review Gate
    displaying hook script + settings.json snippet; user sees no
    question that build-shell would have asked (target-shell,
    invocation-style, setuid, save-path).

12. **Manual smoke — check-hook merged report.** `/build:check-hook`
    on a project containing a hook script produces one findings table
    with the `source` column populated as `FX` or `hook`; Missing
    Tools preamble (if any tool absent) appears once at the top.

13. **Manual smoke — freeform intake still works.**
    `/build:build-shell rotate nginx logs daily using jq on macOS`
    (no `=`, no `--`) runs the normal Elicit for remaining fields
    without crashing; no prior behavior regresses.

14. **Manual smoke — `--emit-only` hard-fails on missing fields.**
    `/build:build-shell target=bash-3.2-portable --emit-only` exits
    with a clear error naming missing fields; does not prompt
    interactively.

15. **PR is open.** `gh pr view` returns a PR referencing `#327`
    with green CI.
