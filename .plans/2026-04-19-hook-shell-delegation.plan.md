---
name: Hook Pair Delegates Shell Concerns to Shell Pair
description: Refactor /build:build-hook and /build:check-hook to reference /build:build-shell and /build:check-shell for generic shell script scaffolding and lints, keeping only hook-specific content in the hook pair.
type: plan
status: draft
branch: feat/327-hook-shell-delegation
related:
  - .plans/2026-04-19-build-check-shell-skill-pair.plan.md
---

# Hook Pair Delegates Shell Concerns to Shell Pair

## Goal

After this refactor, `/build:build-hook` and `/build:check-hook` contain
only hook-specific content (stdin JSON payload, `tool_input` field paths,
matcher casing, `settings.json` wiring, Stop-hook guards, hook exit-code
semantics, CVE-2025-59536, platform limitations). Generic shell-script
concerns (strict-mode preamble, quoting, traps, style, `shellcheck` /
`shfmt` invocation, the 14 FX lints) are referenced by pointer into the
shell pair. Behavior does not regress — every existing Safety Check rule
and every existing check-hook lint continues to fire, either in the hook
pair or via a named pointer to the shell pair.

Closes #327.

## Scope

Must have:

- `plugins/build/skills/build-hook/SKILL.md` — generic script scaffolding
  content compressed. Draft section points at build-shell for shebang,
  `set -Eeuo pipefail`, ERR/EXIT traps, style conventions (`lower_case`
  / `UPPER_CASE` / stderr / `main`), and `|| true` guard. Hook-specific
  content (Draft's stdin / jq / `updatedInput` / settings.json blocks)
  stays verbatim. Safety Check item #8 (ShellCheck + shfmt) becomes a
  one-line "run `/build:check-shell` for general shell lints" pointer.
- `plugins/build/skills/check-hook/SKILL.md` — delegable lints replaced
  by a single "Generic shell lints" entry at the top of the numbered
  checks, naming `/build:check-shell` as the source of truth for
  quoting, preamble, `shellcheck` / `shfmt`, stderr, shebang, `[[` vs
  `[`, and the rest of the 14 FX lints. Remaining numbered checks are
  hook-specific only. `set -x` payload-leak, unquoted payload-derived
  vars specifically (as distinct from generic S1), and any gap where
  check-shell lacks a direct delegate (e.g., explicit missing
  strict-mode preamble as a standalone lint) stay in check-hook.
- `plugins/build/skills/build-shell/SKILL.md` — one-line cross-reference
  in the Route section noting `/build:build-hook` is the event-driven
  specialization that builds on build-shell's script shape.
- `plugins/build/skills/check-shell/SKILL.md` — one-line cross-reference
  in the opening paragraph or Route-equivalent noting `/build:check-hook`
  is the event-driven specialization.
- `plugins/build/pyproject.toml` and `plugins/build/.claude-plugin/plugin.json`
  bumped to 0.5.0 (minor — behavioral change to existing skills).
- All four SKILL.md files pass `/build:check-skill` with zero
  fail-level findings. Warns acceptable if documented.

Won't have:

- New lints added to check-shell to close the "missing preamble" gap
  — that is scope creep; the existing check-hook check-11 stays in the
  hook pair for now.
- Refactoring `/build:check-hook`'s Python / Python-hook guidance (the
  `sys.exit(2)` / uncaught-exception branches) — those are handler-type
  specific, not general shell concerns. They stay.
- Pulling content out of `references/platform-limitations.md` or
  `references/hook-testing.md` — those are already hook-specific.
- Touching `/build:build-subagent`, `/build:build-rule`, or other
  primitives.
- Changing the user-facing slash-command surface. Each skill remains
  callable standalone; delegation is by reference-in-prose, not by
  skill invocation.
- Adding integration tests, fixtures, or new reference files. This is
  a pure markdown refactor.
- `.claude-plugin/marketplace.json` changes (version references the
  plugin, not the skill).

## Approach

Delegation is **by reference**, not by skill invocation — the hook pair
continues to be single-skill from the user's perspective. Replace
duplicated prose with one-line pointers of the form "see `/build:build-shell`
for the generic script scaffold" or "run `/build:check-shell` first;
this skill's checks are hook-specific."

Work the pair in parallel (build-hook + check-hook in one pass each),
since the delete decisions mirror each other. Before each deletion,
confirm the equivalent content exists in the shell pair's SKILL.md. If
a delegate does not exist, keep the content in the hook pair and note
the asymmetry in the plan's Validation section (we are explicitly not
expanding check-shell in this work).

Cross-references in the shell pair are short additions, not a
restructure — one line each in build-shell and check-shell pointing at
the hook pair as the event-driven specialization. The existing "Not for
Claude Code hooks — route to `/build:build-hook`" language already
handles the negative-routing direction; the new lines handle the
positive-"builds-on" direction.

Self-audit the four SKILL.md files with `/build:check-skill` before
committing the version bump. If check-skill flags fail-level issues
introduced by the edits, fix in-place and re-audit.

## File Changes

| File | Change |
|------|--------|
| `plugins/build/skills/build-hook/SKILL.md` | Modify — compress Draft's generic script content (lines ~74-85, 117-133) and Safety Check #8 into pointers to build-shell. Keep all hook-specific content verbatim. |
| `plugins/build/skills/check-hook/SKILL.md` | Modify — replace delegable numbered checks (#11 generic preamble beyond hook-specific concern, #14 ShellCheck/shfmt, parts of #15 a/b/d) with a single "Generic shell lints — delegated to `/build:check-shell`" entry. Keep hook-specific checks verbatim. |
| `plugins/build/skills/build-shell/SKILL.md` | Modify — add one-line cross-reference pointing at build-hook as the event-driven specialization. |
| `plugins/build/skills/check-shell/SKILL.md` | Modify — add one-line cross-reference pointing at check-hook. |
| `plugins/build/pyproject.toml` | Modify — version `0.4.0` → `0.5.0`. |
| `plugins/build/.claude-plugin/plugin.json` | Modify — version `0.4.0` → `0.5.0`. |

No new files. No deletions.

## Tasks

### Task 1: Refactor build-hook Draft to delegate generic script scaffolding

Modify `plugins/build/skills/build-hook/SKILL.md` §3 Draft. Keep the
`INPUT=$(cat)` line, the `tool_input` jq path table, the "Safe payload
extraction" block, `updatedInput` / broader JSON output contract, and
the settings.json entry block verbatim — all hook-specific.

Compress to pointer: the bare script shell (shebang, `set -Eeuo pipefail`,
style conventions for `lower_case` / `UPPER_CASE` / stderr / `main`,
ERR/EXIT traps with `${LINENO}` / `${BASH_COMMAND}`, `set -x` caveat
except the payload-leak nuance, `|| true` guard language, `[[` vs `[`
language). Replace with one paragraph along the lines of:

> The hook script body uses the general-purpose shell scaffold from
> `/build:build-shell` — strict-mode preamble (`set -Eeuo pipefail`),
> quoted expansions (`"${var}"`), ERR/EXIT traps, `lower_case` locals
> / `UPPER_CASE` exports / `main()` + self-sourcing guard. See that
> skill for the template. The hook-specific additions to that scaffold
> are documented below.

Keep the `set -x` warning — its payload-leak framing is hook-specific.

**Verify:** `wc -l plugins/build/skills/build-hook/SKILL.md` shows
reduction of 40+ lines vs pre-edit (was 449). Grep for `set -Eeuo` —
should appear at most once in context of delegation.

Commit: `refactor(build): delegate generic script scaffold in build-hook to build-shell`

### Task 2: Refactor check-hook numbered checks to delegate generic lints

Modify `plugins/build/skills/check-hook/SKILL.md` §4 Checks. Insert a
new first numbered entry "Generic shell lints (delegated)" that names
`/build:check-shell` as the source for the 14 FX lints, `shellcheck`,
`shfmt`, and the Missing Tools preamble. Shift subsequent numbers down.

Replace or collapse:
- Check #11 (Script safety preamble) — keep the missing-strict-mode
  and `|| true` portions (no direct check-shell equivalent), but
  reframe as "hook-specific addition to the generic preamble
  delegated to check-shell."
- Check #12 (Injection safety) — keep the `eval` on payload-derived
  value portion (hook-specific); delegate the unquoted-variable
  portion to check-shell S1.
- Check #14 (ShellCheck static analysis) — delete entirely; delegated.
- Check #15 (Script style) — keep (c) `set -x` (payload-leak
  framing is hook-specific). Delete (a) stderr, (b) `[[` vs `[`,
  (d) shebang — delegated to check-shell D6 / implicit.

Renumber the remaining checks consecutively. Update the "Run sixteen
checks" count in §4 opening line.

**Verify:** `wc -l plugins/build/skills/check-hook/SKILL.md` shows
reduction of 30+ lines vs pre-edit (was 231). Grep for `shellcheck`
— should appear only in the delegation pointer, not in prose
instructions.

Commit: `refactor(build): delegate generic lints in check-hook to check-shell`

### Task 3: Add bidirectional cross-references in shell pair

Modify `plugins/build/skills/build-shell/SKILL.md` — under the existing
"This skill is not for Claude Code hooks — `/build:build-hook` owns that
lifecycle" paragraph, add a complementary positive line:

> `/build:build-hook` builds **on** this scaffold for the event-driven
> hook case — its script shape is this shape plus hook-specific additions
> (stdin JSON payload, `tool_input` extraction, `updatedInput` JSON
> contract).

Modify `plugins/build/skills/check-shell/SKILL.md` — mirror the addition
in the opening paragraph near the existing hook-routing note.

**Verify:** `grep -c "build-hook" plugins/build/skills/build-shell/SKILL.md`
and `grep -c "check-hook" plugins/build/skills/check-shell/SKILL.md`
each return ≥ 2 (existing negative-routing line + new positive-routing
line).

Commit: `docs(build): cross-reference hook pair from shell pair`

### Task 4: Self-audit with check-skill

Run `/build:check-skill` against each of the four SKILL.md files. For
any fail-level finding, fix in-place and re-audit. Warns acceptable if
they existed pre-refactor.

**Verify:** Zero fail-level findings across all four files.

No commit (fixes roll into whichever task's commit applies; if no
changes needed, skip).

### Task 5: Bump build plugin version to 0.5.0

Edit `plugins/build/pyproject.toml` and
`plugins/build/.claude-plugin/plugin.json`: `0.4.0` → `0.5.0`.

**Verify:** `grep version plugins/build/pyproject.toml
plugins/build/.claude-plugin/plugin.json` shows `0.5.0` in both.

Commit: `chore(build): bump to 0.5.0 for hook-shell delegation refactor`

### Task 6: Open PR

Push branch and open PR referencing #327. PR body summarizes the
refactor, links to the plan file, and reproduces the scope-boundary
list from this plan's Won't-have.

**Verify:** PR URL returned; CI green (ruff).

No commit.

## Validation

1. **Line-count reduction is real.**
   `wc -l plugins/build/skills/{build,check}-hook/SKILL.md` shows a
   combined reduction of 70+ lines vs pre-refactor baseline
   (449 + 231 = 680 → target ≤ 610).

2. **Generic scaffold prose is gone from build-hook.**
   `grep -n "lower_case_with_underscores\|UPPER_CASE_WITH_UNDERSCORES"
   plugins/build/skills/build-hook/SKILL.md` returns zero matches.

3. **ShellCheck/shfmt prose is gone from check-hook except as pointer.**
   `grep -cn "shellcheck\|shfmt" plugins/build/skills/check-hook/SKILL.md`
   returns ≤ 3 (one in the delegation pointer, at most two remaining in
   asymmetry-justified hook-specific contexts). Baseline pre-edit is 10+.

4. **Bidirectional cross-references exist.**
   `grep -n "build-hook" plugins/build/skills/build-shell/SKILL.md`
   returns ≥ 2 matches. Likewise `grep -n "check-hook"
   plugins/build/skills/check-shell/SKILL.md`.

5. **Hook-specific content survives verbatim.**
   Every one of these tokens still appears in the post-refactor
   check-hook SKILL.md:
   - `INPUT=$(cat)`
   - `tool_input`
   - `stop_hook_active`
   - `updatedInput`
   - `CVE-2025-59536`
   - `PostToolUse`
   - `Copilot` (or `toolArgs`)
   - `permissionDecision`

   Verified with `grep -l` per-token.

6. **check-skill self-audit is clean.**
   `/build:check-skill` on each of the four SKILL.md files shows zero
   fail-level findings. Any warns are acknowledged (pre-existing or
   documented as accepted).

7. **Version bump is coherent.**
   `grep version plugins/build/pyproject.toml
   plugins/build/.claude-plugin/plugin.json` — both show `0.5.0`.

8. **Smoke: hook-pair invocation flow is still single-skill.**
   Read-through of build-hook SKILL.md §3-9 confirms no step instructs
   the reader to *invoke* `/build:build-shell` (only to *reference* it).
   Likewise for check-hook.
