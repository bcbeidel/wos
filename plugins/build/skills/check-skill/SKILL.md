---
name: check-skill
description: >-
  Use when the user wants to "audit a skill", "review a skill", or
  "improve a skill". Audits a Claude Code SKILL.md for format
  compliance, content quality, and cross-skill description collisions
  across three tiers (deterministic scripts → LLM rubric →
  cross-skill conflict).
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[path/to/SKILL.md or skills/ directory — scans the plugin's skills when omitted]"
user-invocable: true
version: 1.0.0
owner: build-plugin
references:
  - ../../_shared/references/skill-best-practices.md
  - references/check-best-practices-doc-restatement.md
  - references/check-clarity-and-consistency.md
  - references/check-description-retrieval-signal.md
  - references/check-example-realism.md
  - references/check-failure-handling.md
  - references/check-mechanical-work-partition.md
  - references/check-prerequisites-and-contract.md
  - references/check-safety-gating.md
  - references/check-step-discipline.md
  - references/check-trigger-conditions.md
license: MIT
---

# /build:check-skill

Evaluate the quality of an existing Claude Code skill. Three tiers, in order: deterministic format checks (no LLM), per-skill semantic checks (ten always-on dimensions in a single locked-rubric call), then cross-skill description collision detection.

This skill follows the [check-skill pattern](../../_shared/references/check-skill-pattern.md). Tier-1 detection is in 8 per-skill scripts emitting JSON envelopes via `_common.py` plus three shared detectors (`_shared/scripts/check_handoff_shape.py`, `_shared/scripts/check_reference_lead.py`, and `_shared/scripts/check_evaluator_policy_echo.py`, all invoked with `--envelope`), 24 rule_ids total. Tier-2 has 10 judgment dimensions read inline by the primary agent. Tier-3 is a judgment-driven cross-skill description-collision pass over candidate pairs.

The audit rubric mirrors the authoring principles in [skill-best-practices.md](../../_shared/references/skill-best-practices.md). Each Tier-2 dimension cites its source principle. When the principles doc changes, the dimensions should follow.

## When to use

Also fires when the user phrases the request as:

- "check skill quality"
- "find problems in a skill"

## Workflow

### 1. Discover Skills

Skill files are SKILL.md anywhere under `plugins/<plugin>/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, or `~/.claude/skills/<name>/SKILL.md`.

When `$ARGUMENTS` resolves to a path, scope discovery to that file or directory. When `$ARGUMENTS` is empty, scan the current plugin's skills directory.

Report: "Found N skills. Auditing..."

### 2. Tier-1 Deterministic Format Checks

Invoke 10 detection scripts:

```bash
SCRIPTS="${SKILL_DIR}/scripts"
SHARED_SCRIPTS="${SKILL_DIR}/../../_shared/scripts"
TARGETS="$ARGUMENTS"

bash    "$SCRIPTS/check_identity.sh"           $TARGETS   # 5 rules: filename, directory-basename, name-slug, reserved-names, name-uniqueness
bash    "$SCRIPTS/check_frontmatter.sh"        $TARGETS   # 4 rules: required-frontmatter, version-shape, description-cap, license-presence
bash    "$SCRIPTS/check_structure.sh"          $TARGETS   # 3 rules: required-sections, steps-shape, examples-content
bash    "$SCRIPTS/check_size.sh"               $TARGETS   # 2 rules: body-length (warn ≥300, fail ≥400), line-length
bash    "$SCRIPTS/check_prose.sh"              $TARGETS   # 2 rules: prose-hedge, absolute-path
bash    "$SCRIPTS/check_secret.sh"             $TARGETS   # 1 rule:  secret
bash    "$SCRIPTS/check_dangerous_patterns.sh" $TARGETS   # 2 rules: remote-exec, destructive-cmd
python3 "$SCRIPTS/check_cisco.py"              $TARGETS   # 2 rules: scanner-fail, scanner-warn (inapplicable when scanner missing)
python3 "$SHARED_SCRIPTS/check_handoff_shape.py"           --envelope $TARGETS   # 1 rule:  handoff-shape
python3 "$SHARED_SCRIPTS/check_reference_lead.py"          --envelope $TARGETS   # 1 rule:  reference-lead-echo (walks each SKILL.md's sibling references/)
python3 "$SHARED_SCRIPTS/check_evaluator_policy_echo.py"   --envelope $TARGETS   # 1 rule:  evaluator-policy-echo
```

Each script emits a JSON array of envelopes: `{rule_id, overall_status, findings[]}`. `recommended_changes` is canonical — copy through verbatim.

**Script-to-rules map** (24 Tier-1 rule_ids):

| Script | rule_ids | Severity |
|---|---|---|
| `check_identity.sh` | `filename` | fail |
| `check_identity.sh` | `directory-basename` | fail |
| `check_identity.sh` | `name-slug` | fail |
| `check_identity.sh` | `reserved-names` | fail |
| `check_identity.sh` | `name-uniqueness` | fail |
| `check_frontmatter.sh` | `required-frontmatter` | fail |
| `check_frontmatter.sh` | `version-shape` | fail |
| `check_frontmatter.sh` | `description-cap` | fail |
| `check_frontmatter.sh` | `license-presence` | warn |
| `check_structure.sh` | `required-sections` | fail |
| `check_structure.sh` | `steps-shape` | fail (not ordered) / warn (non-sequential) |
| `check_structure.sh` | `examples-content` | warn |
| `check_size.sh` | `body-length` | warn (≥300) / fail (≥400) |
| `check_size.sh` | `line-length` | warn |
| `check_prose.sh` | `prose-hedge` | warn |
| `check_prose.sh` | `absolute-path` | warn |
| `check_secret.sh` | `secret` | fail |
| `check_dangerous_patterns.sh` | `remote-exec` | warn |
| `check_dangerous_patterns.sh` | `destructive-cmd` | warn |
| `check_cisco.py` | `scanner-fail` | fail |
| `check_cisco.py` | `scanner-warn` | warn |
| `_shared/scripts/check_handoff_shape.py` | `handoff-shape` | warn |
| `_shared/scripts/check_reference_lead.py` | `reference-lead-echo` | warn |
| `_shared/scripts/check_evaluator_policy_echo.py` | `evaluator-policy-echo` | warn |

**Tier-2 exclusion list.** Any FAIL in `filename`, `directory-basename`, `name-slug`, `reserved-names`, `required-frontmatter`, `version-shape`, `description-cap`, `required-sections`, `body-length` (>400 line case), `secret`, or `scanner-fail` excludes the skill from Tier-2 — malformed skills don't reach the LLM step.

**Missing-tool degradation.** `check_cisco.py` emits envelopes with `overall_status: inapplicable` and exits 0 when `cisco-ai-skill-scanner` is absent. The remaining scripts continue.

### 3. Tier-2 Semantic Dimensions (One LLM Call per Skill)

For each structurally valid skill, evaluate against the **10 judgment rules** at `references/check-*.md`:

| File | Dimension | Severity |
|---|---|---|
| [check-description-retrieval-signal.md](references/check-description-retrieval-signal.md) | D1 — description fires on the user's situation, not the skill's function | warn |
| [check-trigger-conditions.md](references/check-trigger-conditions.md) | D2 — `When to use` carries concrete trigger phrases | warn |
| [check-step-discipline.md](references/check-step-discipline.md) | D3 — steps are an ordered, action-led sequence | warn |
| [check-clarity-and-consistency.md](references/check-clarity-and-consistency.md) | D4 — direct prose; consistent terminology | warn |
| [check-prerequisites-and-contract.md](references/check-prerequisites-and-contract.md) | D5 — prereqs named; handoff contract explicit | warn |
| [check-failure-handling.md](references/check-failure-handling.md) | D6 — failure modes named with recovery paths | warn |
| [check-safety-gating.md](references/check-safety-gating.md) | D7 — destructive ops gate on user confirmation | warn |
| [check-example-realism.md](references/check-example-realism.md) | D8 — examples use domain-specific identifiers | warn |
| [check-mechanical-work-partition.md](references/check-mechanical-work-partition.md) | D9 — mechanical work in scripts; judgment in SKILL.md | warn |
| [check-best-practices-doc-restatement.md](references/check-best-practices-doc-restatement.md) | D10 — SKILL.md cites `*-best-practices.md`; does not restate principles | warn |

#### Evaluator policy

- **Single locked-rubric pass per skill.** Read all 9 rule files first, then evaluate each skill in turn against the unified rubric. A single locked-rubric pass produces stable scoring.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`, not `pass`.
- **Severity floor: WARN.** All 9 Tier-2 dimensions are coaching, not blocking. Escalate to FAIL only for safety concerns Tier-1 missed.
- **One finding per dimension per skill maximum.** Surface the highest-signal location with concrete excerpts.

Include the full SKILL.md verbatim — never summarize. Dimensions that don't apply (e.g., D7 Safety Gating on a skill with no destructive ops; D8 Example Realism on a skill with no examples) return `inapplicable` silently.

### 4. Tier-3 Cross-Skill Description Collision

For every pair of skills in the audit scope (always-on against always-on, or `description`s sharing trigger-phrase tokens), evaluate whether the descriptions retrieve on the same caller situation. Collisions surface as `warn` per pair — the user resolves by narrowing either side; the auditor never picks a winner.

Tier-3 returns `inapplicable` silently when the audit scope holds only one skill.

### 5. Report Findings

Merge findings from all 3 tiers into a unified table:

```
| Tier | rule_id | Location | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; Tier-1 before Tier-2 before Tier-3 within severity. Each finding's `Recommendation:` line copies through `recommended_changes` verbatim.

Close with: `N skills audited, M findings (X fail, Y warn)` or `N skills audited — no findings`.

### 6. Opt-In Repair Loop

Ask exactly once:

> "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:

- **Direct edit** — frontmatter shape, slug correction, missing-section insertion, hedged phrasing rewording. Show diff; write on confirmation.
- **Routed to another skill** — substantial rewrites → `/build:build-skill` for scaffold-from-scratch.
- **Tier-2/3 judgment** — description retrieval, trigger conditions, etc. Ask the user; rewrite the section; show diff; write on confirmation.

After each applied fix, re-run the relevant Tier-1 script (or re-judge the Tier-2/3 dimension). Terminate when the user enters `n` or exhausts findings.

## Anti-Pattern Guards

1. **Per-dimension LLM call.** Use one locked-rubric call per skill — a unified rubric produces stable scoring.
2. **LLM-evaluating format compliance.** Frontmatter shape, slug syntax, body length — handle deterministically in Tier-1; send only structurally valid skills to the LLM.
3. **Ambiguous compliance reported as PASS.** Surface as WARN (default-closed).
4. **Vague finding text.** Cite the specific SKILL.md and the exact phrasing or field that triggered the finding.
5. **Cross-skill collision-comparing skills with disjoint descriptions.** Gate Tier-3 on co-fire potential (overlapping trigger phrases or both always-on).
6. **Trigger-gating Tier-2 dimensions.** Don't skip dimensions based on whether the skill "opts into" a shape; run all 9. Dimensions that don't apply return `inapplicable` silently.
7. **Re-evaluating scripted rules in Tier-2.** Scripts are authoritative for the 22 Tier-1 rules; trust the `pass` envelope.
8. **Suppressing the inapplicable envelope.** When the cisco scanner is missing, surface `inapplicable` — do not silently skip.
9. **Embellishing scripts' `recommended_changes`.** Each rule's recipe constant is canonical guidance sourced from `skill-best-practices.md`. Copy it through.

## Key Instructions

- Run Tier-1 deterministic checks first; gate LLM evaluation on structural validity.
- Present all 10 Tier-2 dimensions as a single locked-rubric call per skill.
- Include the full SKILL.md verbatim in every LLM evaluation.
- Limit Tier-3 collision comparison to skill pairs that could co-fire.
- Surface borderline evidence as WARN (default-closed).
- Recovery: read-only outside the Repair Loop; edits revertable via `git diff` / `git checkout`.

## Handoff

**Chainable to:** `/build:build-skill` (rebuild non-compliant skills from scratch when targeted repair would exceed the skill's scope); `/build:check-skill-pair <primitive>` (audit pair-level integrity for build/check pairs).
