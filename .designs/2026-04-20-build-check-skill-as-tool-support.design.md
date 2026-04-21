---
name: build-skill and check-skill support for --as-tool pattern
description: Teach /build:build-skill to scaffold the --as-tool dual-invocation pattern and /build:check-skill to audit it. Opt-in via `skill-invocable: true` frontmatter; inline contract declares DATA or ARTIFACT return shape (ARTIFACT supports multi-artifact via N fenced blocks); shared mechanism spec at plugins/build/_shared/references/as-tool-contract.md.
type: design
status: approved
related:
  - .research/2026-04-20-emit-only-invocation-prior-art.research.md
---

# build-skill and check-skill Support for `--as-tool` Pattern

## Purpose

Teach `/build:build-skill` and `/build:check-skill` to treat the `--as-tool` dual-invocation pattern as a first-class skill shape. Skill authors who want their skill to be callable by another skill opt in via frontmatter; the scaffolder asks during intake and generates the contract section; the auditor verifies declared contracts are consistent and complete.

## Why Now

- The `--as-tool` pattern was validated empirically on 2026-04-20 (PR #333 + PR #334). Fresh-session test confirmed real runtime invocation — 4 distinct skill loads + 4 Bash tool invocations when `/dummy:greet-team` invoked `/dummy:greet --as-tool` per teammate, in parallel. Mechanism (a) is proven.
- Prior-art research (`.research/2026-04-20-emit-only-invocation-prior-art.research.md`, on `explore/327-structured-invocation-thinking`) established `--as-tool` as the LCD name (OpenAI Agents SDK `as_tool`, LangGraph subgraph-as-tool, Semantic Kernel agent-as-KernelFunction all converge on the metaphor).
- Downstream consumers (issue #327 hook/shell refactor, future Python-script pair per #326) want to invoke the pattern. Without build-skill scaffolding it and check-skill auditing it, adoption relies on each author remembering the shape. High drift risk.
- Ecosystem-wide adoption pressure is **not** the goal yet. Default-off opt-in gives us one skill at a time to refine the pattern before it's everywhere.

## Locked Decisions

1. **Default: pattern-OFF, opt-in via frontmatter.** Absence means human-only.
2. **Frontmatter field: `skill-invocable: true`**. Parallels existing `user-invocable`. Two independent axes.
3. **Contract location: inline in SKILL.md** under standardized `## --as-tool contract` section.
4. **check-skill severity: fail on hard inconsistency, warn on completeness.** Declared-but-missing contract = fail; missing subsection = warn.
5. **Ship together:** contract doc + build-skill/check-skill updates in one PR.

## Behavior

### New `skill-invocable` frontmatter field

Boolean. Defaults to `false` when absent.

- `skill-invocable: true` declares the skill supports `--as-tool` invocation per the shared contract. Requires a `## --as-tool contract` section in the body.
- `skill-invocable: false` or absent declares the skill is human-only. No `--as-tool` scaffolding or audit applies.

Independent of `user-invocable`. Valid combinations:
- `user-invocable: true` + `skill-invocable: false` — human-only slash-command skill (most existing skills, default).
- `user-invocable: true` + `skill-invocable: true` — dual-invocation (new pattern; dummy plugin).
- `user-invocable: false` + `skill-invocable: true` — purely programmatic, no slash command (rare; not scaffolded by default; the auditor recognizes it).
- `user-invocable: false` + `skill-invocable: false` — non-invocable (doesn't belong in `skills/`; auditor warns).

### Return shapes: DATA vs ARTIFACT

Every `--as-tool` skill emits a JSON envelope for control flow (`Success` / `NeedsMoreInfo` / `Refusal` — always structured). What differs is the **Success payload**:

- **Shape DATA** — structured data skill (e.g., `/dummy:greet`, `/build:check-skill`). `Success` JSON contains a `value` field with a skill-declared schema. No fenced block.
- **Shape ARTIFACT** — skill whose output is a text artifact in its native syntax (e.g., `/build:build-shell` produces a shell script, `/build:build-rule` produces a markdown file). `Success` JSON is a control envelope; the artifact body follows as one or more fenced code blocks.

`NeedsMoreInfo` and `Refusal` are **always JSON-only regardless of shape** — no fenced block. This keeps the failure-path contract uniform.

**Shape DATA — success emission:**
```
{"type": "Success", "value": {"text": "Good morning, bob!", ...}}
```

**Shape ARTIFACT — single-artifact success emission:**
```
{"type": "Success", "artifact_types": ["text/x-shellscript"], "metadata": {"target": "bash-3.2-portable"}}
```
```bash
#!/usr/bin/env bash
# ... the scaffold ...
```

**Shape ARTIFACT — multi-artifact success emission** (e.g., `/build:build-hook` producing both a hook script and a settings.json entry):
```
{"type": "Success", "artifact_types": ["text/x-shellscript", "application/json"], "metadata": {"hook_event": "PreToolUse"}}
```
```bash
#!/usr/bin/env bash
# hook script
```
```json
{"hooks": {"PreToolUse": [...]}}
```

Rule: the number and order of fenced blocks match the `artifact_types` array exactly. Each fenced block's language tag matches the declared MIME type (e.g., `application/json` → ` ```json `, `text/x-shellscript` → ` ```bash `, `text/markdown` → ` ```markdown `). The caller LLM reads the JSON first, then each fenced block in declared order.

### Standardized `## --as-tool contract` section

When `skill-invocable: true`, the skill body must include the section. Shape:

```markdown
## `--as-tool` contract

**Required fields:**
- `<field>` — description
- `<field>` — description

**Return shape:** DATA | ARTIFACT
- (if ARTIFACT) **Artifact types:** `text/x-shellscript`, `application/json`, ... (ordered).
- `Success` — (DATA) describes `value` schema | (ARTIFACT) describes metadata fields and each fenced block's role.
- `NeedsMoreInfo` — `missing: [...]`, `hint: "..."` (JSON only, always).
- `Refusal` — categories used (`scope-gate`, `permission`, etc.) (JSON only, always).

**Side effects:** list or "none" (e.g., reads file X, invokes /foo --as-tool).

**Parallel-safe:** `yes` (default) or `no` + reason.
```

All four subsections expected. Missing Return shape declaration or artifact-types on an ARTIFACT skill → fail. Missing Side effects or Parallel-safe → warn.

### `/build:build-skill` changes

**Two-level intake** at Capture Intent or Interview phase:

1. **Opt-in question:** "Should this skill be invocable by other skills via `--as-tool`? (y/N)". Default no — matches opt-in posture.
2. **Shape question** (only if yes to #1): "Does this skill return structured data (DATA) or a text artifact like a script or markdown file (ARTIFACT)?". If ARTIFACT: "What artifact types? (e.g., `text/x-shellscript`, `text/markdown`, `application/json` — comma-separated if multiple)".

If **opted in**:
- Set `skill-invocable: true` in frontmatter; add `../../_shared/references/as-tool-contract.md` to `references:`.
- Elicit required fields list, Success schema (DATA) or artifact-roles (ARTIFACT), side-effect list, parallel-safety.
- Generate `## --as-tool contract` in the body with the declared shape.
- Generate a mode-branched Workflow (`§Xa. Human mode` / `§Xb. --as-tool mode`), with the `--as-tool mode` step documenting the specific emission format (JSON only for DATA; JSON + N fenced blocks for ARTIFACT).
- Generate Key Instructions entries enforcing mode-specific rules (emit JSON only for DATA; emit JSON-envelope-plus-fenced-blocks for ARTIFACT; hard-fail with `NeedsMoreInfo` on missing required fields; JSON-only on `NeedsMoreInfo` / `Refusal` regardless of shape).

If **not opted in**: scaffold proceeds as today; no new frontmatter; no contract section.

The scaffolded SKILL.md template has two variants (DATA and ARTIFACT) because the emission prose differs. Both variants share the envelope shape for failure cases.

### `/build:check-skill` changes

New checks (additive to the existing 22):

| # | Check | Severity | Fires when |
|---|---|---|---|
| 23 | `skill-invocable` frontmatter present and boolean | warn | field present but non-boolean value |
| 24 | Declared `skill-invocable: true` has a `## --as-tool contract` section | **fail** | field true, section missing or empty |
| 25 | Contract section declares Return shape (DATA or ARTIFACT) | **fail** | section present but no `**Return shape:** DATA` or `ARTIFACT` line |
| 26 | Contract section documents all three cases (Success / NeedsMoreInfo / Refusal) | **fail** | any case missing from the Return-shape subsection |
| 27 | ARTIFACT shape declares `Artifact types:` with at least one MIME type | **fail** | Return shape is ARTIFACT but artifact types are missing or empty |
| 28 | Contract section documents Required fields | warn | section present but Required fields list empty or missing |
| 29 | Contract section documents Side effects | warn | section present but subsection absent |
| 30 | Contract section documents Parallel-safe | warn | section present but subsection absent |
| 31 | `user-invocable: false` + `skill-invocable: false` (non-invocable skill) | warn | both false or both absent |

Skills with `skill-invocable: false` or absent: checks 24–30 do not fire. Check 31 only fires on the all-false pathology.

### Shared mechanism spec

New file: `plugins/build/_shared/references/as-tool-contract.md`.

Skill-agnostic generic spec:
- `$ARGUMENTS` parsing rule (empty / freeform / `key=value` / `--as-tool`).
- Skip/run-per-step semantics under `--as-tool` (Elicit / Scope Gate / Draft / Safety Check / Review Gate / Save / Test handoff).
- Three-case return envelope (Success / NeedsMoreInfo / Refusal).
- **Two return shapes (DATA and ARTIFACT)** with emission examples for each. DATA: JSON only. ARTIFACT: JSON envelope + one or more fenced code blocks, with `artifact_types` declared in the envelope, fenced-block order matching, and language tag per MIME type.
- Rule: `NeedsMoreInfo` and `Refusal` are always JSON-only regardless of shape.
- Parallel-safety default (yes unless documented otherwise).
- Freeform-text mode (voice-dictated human input; does not apply under `--as-tool`).
- When to use / when not to use the pattern.
- When to pick DATA vs ARTIFACT (rule of thumb: produces code/markdown/config → ARTIFACT; produces structured records → DATA).

Referenced by build-skill and check-skill (both gain `references:` entry); authors of opted-in skills reference it from their own SKILL.md as well.

## Components

| File | Change |
|---|---|
| `plugins/build/_shared/references/as-tool-contract.md` | **Create** — generic mechanism spec. |
| `plugins/build/skills/build-skill/SKILL.md` | **Modify** — add intake question; scaffold `skill-invocable: true` + `## --as-tool contract` section when opted in; reference shared contract doc. |
| `plugins/build/skills/check-skill/SKILL.md` | **Modify** — add seven new checks (23–29); reference shared contract doc. |
| `plugins/build/skills/build-skill/references/skill-writing-guide.md` | **Modify** — add section on the dual-invocation pattern; point to `as-tool-contract.md` for the full spec. |
| `plugins/build/pyproject.toml` | **Modify** — `0.4.0` → `0.5.0`. |
| `plugins/build/.claude-plugin/plugin.json` | **Modify** — `0.4.0` → `0.5.0`. |
| Python lint code (`plugins/build/src/check/...`) | **Modify if applicable** — static checks that verify frontmatter shape may need to learn about `skill-invocable`. |

## Constraints

### Must have

- Shared mechanism spec exists and is referenced by build-skill, check-skill, and any scaffolded opted-in skill.
- build-skill asks the opt-in question during intake for every new skill; scaffolds the contract section when answered yes.
- check-skill's new checks 23–29 fire per the severity calibration; no regression on existing checks 1–22.
- All 41 existing SKILL.md files pass `/build:check-skill` with zero **new** fail-level findings (absence of `skill-invocable` = no new checks fire on them).
- Build plugin bumps to 0.5.0; both `pyproject.toml` and `.claude-plugin/plugin.json` updated.
- The `--as-tool contract` section shape is stable and documented in the shared spec so authors can copy-paste it into future skills.

### Won't have

- **Migration of existing skills.** No bulk-adding `skill-invocable: false` to the 41 existing files. Absent field = default off.
- **Refactor of hook/shell pair** (#327's original scope). This is the precondition; the refactor is downstream.
- **Dummy plugin changes.** `/dummy:greet` and `/dummy:greet-team` stay as proof-of-concept. Their SKILL.md files may not perfectly match the final shape — fine; they're scratch.
- **Retroactive audit of every skill** for hidden `--as-tool` intent. If a skill secretly does dual-invocation but doesn't declare it, check-skill won't notice — and that's acceptable until it becomes a real problem.
- **Python-side parser or validator** for `--as-tool` arguments. The parsing is SKILL-level prose; no runtime harness.
- **check-skill LLM-judgment check** verifying "declared contract matches actual workflow." Out of scope; deterministic presence-checks are enough at this stage. A future iteration can add it.
- **A `/build:as-tool-migrate` skill** to help opt-in existing skills. If demand emerges, separate issue.
- **Enforcement via hook.** This is opt-in; no blocking hook.
- **Cross-plugin invocation test harness.** Dummy plugin already proves it works; no automation needed in this scope.
- **Graduation to required declaration (Q1 option C).** Deferred until the pattern has 3+ real adopters beyond the dummy plugin.

## Acceptance Criteria

Verifiable from outside after the PR merges:

1. **Shared contract file exists.** `test -f plugins/build/_shared/references/as-tool-contract.md` returns 0; the file has six named sections (grep `^## ` returns ≥ 6).

2. **build-skill and check-skill reference the contract.** `grep "as-tool-contract" plugins/build/skills/{build,check}-skill/SKILL.md` returns ≥ 2 lines.

3. **build-skill's intake asks the question.** Reading the updated SKILL.md, there is a visible step prompting "Should this skill be invocable by other skills?" or equivalent.

4. **check-skill documents nine new checks.** The SKILL.md Run-checks section adds checks 23–31 with the severities calibrated per this design (fail on hard inconsistency / missing return-shape declaration / missing artifact-types; warn on completeness gaps).

5. **Existing skills still pass.** Running `/build:check-skill` against the repo (all 41 existing SKILL.md files) produces zero new fail-level findings attributable to the new checks.

6. **Scaffolding produces the expected shape for DATA skills.** A sample run of `/build:build-skill` answered "yes → DATA" produces a SKILL.md with:
   - `skill-invocable: true` in frontmatter
   - `references:` including `../../_shared/references/as-tool-contract.md`
   - `## --as-tool contract` section with `**Return shape:** DATA` and four populated subsections
   - Workflow with `§Xb. --as-tool mode` instructing JSON-only emission

7. **Scaffolding produces the expected shape for ARTIFACT skills.** A sample run of `/build:build-skill` answered "yes → ARTIFACT, types: text/x-shellscript" produces a SKILL.md with:
   - `skill-invocable: true` in frontmatter
   - `## --as-tool contract` section with `**Return shape:** ARTIFACT` and `**Artifact types:** text/x-shellscript`
   - Workflow with `§Xb. --as-tool mode` instructing JSON envelope + single ```bash fenced block emission
   - Multi-artifact variant tested separately with `text/x-shellscript, application/json` producing JSON envelope + two fenced blocks in declared order

8. **Detected inconsistencies fire at the right severity.** Manually constructing test SKILL.md fixtures confirms:
   - `skill-invocable: true` + no contract section → **fail**
   - contract section present but no `Return shape:` declaration → **fail**
   - `Return shape: ARTIFACT` + no `Artifact types:` line → **fail**
   - contract section present but one of the three cases (Success / NeedsMoreInfo / Refusal) missing → **fail**
   - contract section present but Side-effects subsection missing → **warn**
   - `user-invocable: false` + `skill-invocable: false` → **warn**

8. **Dummy plugin still works.** Running `/dummy:greet --as-tool name=bob time-of-day=morning` in a fresh session still returns `Success` JSON. (No regression from the scaffolding/audit changes.)

9. **Version bump is coherent.** `grep version plugins/build/pyproject.toml plugins/build/.claude-plugin/plugin.json` shows 0.5.0 on both.

10. **Self-audit of the two modified skills** — `/build:check-skill` run against `build-skill` and `check-skill` SKILL.md files shows zero new fail-level findings from the edits.

## Open Questions

None blocking. All five key decisions locked during scoping (default-OFF opt-in; `skill-invocable` field; inline contract section; fail-on-hard-inconsistency; ship-together).

Minor tactical items (stated as defaults — flag during plan-work if they need revisiting):

- **Shared contract doc naming:** `as-tool-contract.md` (chosen to match flag name). Alternative `skill-invocable-contract.md` or `emit-only-contract.md` rejected.
- **check-skill number continuity:** new checks are 23–29, additive to existing 22. If renumbering becomes necessary elsewhere, that's a separate concern.
- **build-skill tested_with field:** currently `[sonnet]`. No change needed for this work.
