---
name: check-skill-chain
description: >
  Design a skill-chain from a goal, or check an existing skill-chain manifest
  for structural and contract issues. Use when the user wants to "design a
  skill-chain", "create a workflow", "check a chain manifest", "audit a chain",
  or "repair a chain".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[workflow goal or path/to/manifest.chain.md]"
user-invocable: true
references:
  - references/check-cross-reference.md
license: MIT
---

# Check Skill-Chain

Design a `*.chain.md` manifest from a workflow goal (Goal mode), or audit
an existing manifest for structural and contract correctness (Manifest
mode). Manifest mode follows the [check-skill
pattern](../../_shared/references/check-skill-pattern.md)'s
**design+audit hybrid carve-out** — Goal mode is design-only and outside
pattern scope; Manifest mode is the audit half and conforms to the
Tier-1 / Tier-2 / Evaluator-policy structure.

This skill ships **no scripts of its own**. The Tier-1 structural lint
delegates to `plugins/wiki/scripts/lint.py` (same script `/wiki:lint`
invokes) — that's the canonical authority for chain-manifest
structure. Cross-plugin tool delegation is allowed at Tier-1 per the
pattern's hybrid carve-out; we do not wrap `lint.py` in a thin local
script just to satisfy "scripts/check_*.py owned by this skill".
Inputs are validated by argparse; the wrapped script does not call
subprocess with `shell=True` or take untrusted command strings.

## Workflow

### Detect Mode

- **Argument is a path to a `*.chain.md` file** → **Manifest mode** (audit)
- **No argument, or free-text goal** → **Goal mode** (design)

### Goal Mode

1. **Discover skills** — list available SKILL.md files from `skills/` (and any
   installed plugin `skills/` directories). Present as a numbered list with descriptions.
2. **Structured dialogue** — collect in order:
   - Skill sequence (ordered; user can reorder or add)
   - Output contract per step (what artifact or state does this step produce?)
   - Input requirement per step (what does this step need from the prior step?)
   - Gate condition per consequential step (when does a human review before continuing?)
   - Termination condition (what constitutes chain-complete success?)
   - Negative scope (what does this skill-chain explicitly not do?)
3. **Produce manifest** — write `plans/YYYY-MM-DD-<name>.chain.md`:
   - Frontmatter: `name`, `description`, `type: chain`, `goal`, `negative-scope`
   - Body: `## Steps` pipe table — `| Step | Skill | Input Contract | Output Contract | Gate |`
4. **Hard gate** — present for user review. State: "This is a design artifact — invoke
   `/work:start-work` or run each skill manually to execute." Do not invoke any step.

### Manifest Mode (audit)

#### Tier-1: Deterministic structural checks (delegated)

Run `python3 plugins/wiki/scripts/lint.py --root <project-root>
--no-urls` and extract findings whose `path` matches the target
manifest. The wiki lint covers five structural dimensions of every
chain manifest: skills exist on disk, contracts are declared per step,
gates appear on consequential steps, a termination condition is
present, and there are no cycles. **Do not re-implement these checks
locally** — `lint.py` is the canonical authority.

If `parse_chain()` raises on a malformed manifest, report it as a
`fail` finding and continue. Do not crash.

`lint.py` emits findings in the wiki linter's table format, not the
JSON envelope shape the broader pattern uses. That's acceptable here
because the lint is a cross-plugin shared tool with its own consumers
(e.g., `/wiki:lint`) — translating its output into envelope shape is
out of scope for this skill.

#### Tier-2: Judgment dimension

For each step in the manifest, evaluate against
[references/check-cross-reference.md](references/check-cross-reference.md):
read the step's referenced SKILL.md body; assess whether the declared
`output_contract` is plausible given what the skill actually produces.
Mismatches are always `warn` — never `fail` — because the user (not
the audit) decides whether the manifest's contract or the SKILL.md's
output is the source of truth.

##### Evaluator policy

- **Single locked-rubric pass per artifact.** Read `check-cross-reference.md` first, then evaluate every step in the manifest against the unified rubric. A single locked-rubric pass produces stable scoring.
- **Default-closed when borderline.** When evidence is ambiguous, return `warn`, not `pass`.
- **Severity floor: WARN.** Cross-reference findings are coaching, not blocking. Escalate to FAIL only for safety concerns Tier-1 missed (extremely unusual for a chain manifest — typically not applicable).
- **One finding per step maximum.** If a step has multiple discrepancies (shape and detail and naming), surface the highest-signal one with concrete excerpts from both sides. Bulk findings train the user to disregard the audit.

#### Tier-3: Cross-entity collision

A chain manifest is a single artifact; multi-manifest collision is
out of scope. Tier-3 returns `inapplicable` silently for this skill.

#### Report

Merge Tier-1 (lint.py) and Tier-2 (cross-reference) findings into a
unified table:

```
| File | Issue | Severity |
|------|-------|----------|
```

Summary line: `N fail, N warn`. Sort: `fail` before `warn`; Tier-1 (structural) before Tier-2 (cross-reference) within the same severity.

#### Repair loop

Ask: "Apply fixes? Enter y (all), n (skip), or comma-separated numbers."

For each selected finding:
- **Tier-1 manifest fix** — propose targeted edit, show diff, apply on confirmation.
- **Tier-1 missing-skill** — step references a SKILL.md that doesn't exist. Invoke `/build:build-skill` inline to create it, then re-run `lint.py` to confirm.
- **Tier-2 contract drift** — read the finding's `recommended_changes` field. The fix may be in the manifest (most common — its contract was speculative) or in the SKILL.md (the actual output evolved). Propose targeted edit, show diff, apply on confirmation.

After each applied fix, re-run the relevant Tier (1 or 2) on the
affected scope. Return to the findings table.

Exit when all findings are resolved or the user declines remaining
fixes: "Skill-chain manifest is well-formed — 0 issues found."

## Anti-Pattern Guards

1. **Tier-2 before Tier-1** — `wiki/lint.py` runs first, always; surface structural failures before judgment. A manifest that doesn't parse cleanly cannot be cross-referenced productively.
2. **Bulk repair without per-change confirmation** — each fix requires separate confirmation; never apply more than one change without a confirmation step between them.
3. **Executing the skill-chain in Goal mode** — Goal mode produces a design artifact only; the hard gate must be stated explicitly before exiting.
4. **Treating cross-reference mismatches as `fail`** — Tier-2 findings are `warn`; the user decides whether the contract or the SKILL.md needs updating.
5. **Crashing on malformed manifest** — if parsing fails, report as a `fail` finding and continue; partial or incomplete manifests produce findings, not errors.
6. **Re-implementing `lint.py`'s structural checks locally** — the wiki lint is the canonical authority for chain-manifest structure. Wrap it, don't duplicate it.
7. **Embellishing the cross-reference rule's `recommended_changes`** — the recipe in `check-cross-reference.md` is the canonical guidance. When generating per-finding `recommended_changes`, ground it in the rule's "How to apply" — name the discrepancy, name both sides, suggest a fix. Don't paraphrase the rule body itself.

## Handoff

**Receives:** Free-text workflow goal (goal mode) or path to `*.chain.md` (manifest mode)
**Produces:** Goal mode — `plans/YYYY-MM-DD-<name>.chain.md`. Manifest mode — structured
findings table; optionally, targeted edits applied to the manifest or referenced SKILL.md files.
**Chainable to:** start-work (to run the skill-chain steps), build-skill (gap case in repair loop)

## Key Instructions

- Goal mode is design-only — never invoke a step in the skill-chain; the manifest is the deliverable
- Cross-reference is LLM judgment — flag mismatches as `warn` only; the user decides what to fix
- Per-change confirmation is non-negotiable — never apply more than one fix without separate confirmation
- `scripts/lint.py` structural checks cover 5 dimensions (skills exist, contracts declared, gates
  on consequential steps, termination condition, no cycles) — do not re-implement them
- Won't: execute skill-chain steps, bulk-apply fixes, or treat cross-reference mismatches as hard failures
