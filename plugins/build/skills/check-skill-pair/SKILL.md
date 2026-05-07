---
name: check-skill-pair
description: >
  Audits pair-level integrity of a primitive-pair (the artifact
  `/build:build-skill-pair` produces) by walking the four required
  artifact slots — principles doc, `build-<primitive>/SKILL.md`,
  `check-<primitive>/SKILL.md`, and the `primitive-routing.md`
  registration — and reports cross-artifact issues a per-SKILL.md
  checker cannot see: missing principles doc, divergent principles
  paths between halves, absent routing registration, missing
  build→check handoff. Per-half structural compliance with the
  unified pattern (`check-skill-pattern.md`) is delegated to
  `plugins/build/_shared/scripts/check_skill_pattern.py`.
  Use when the user wants to "audit a skill pair", "review a
  primitive pair", or "validate the skill pair for X". Not for
  auditing a single SKILL.md — route to `/build:check-skill`. Not
  for re-distilling a stale principles doc — route to
  `/build:build-skill-pair`.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
argument-hint: "[primitive-name]"
references:
  - ../../_shared/references/brief-best-practices.md
  - ../../_shared/references/check-skill-pattern.md
  - ../../_shared/references/primitive-routing.md
  - ../../_shared/references/skill-locations.md
  - ../../_shared/references/skill-pair-best-practices.md
  - references/check-brief-content-quality.md
license: MIT
---

# Check Skill Pair

Audit a primitive-pair for cross-artifact integrity. Per-SKILL.md
concerns (description quality, frontmatter shape, body length) are
covered by `/build:check-skill`. Per-half structural pattern
compliance is covered by
`plugins/build/_shared/scripts/check_skill_pattern.py`. This skill
catches the issues that only surface when you look at the four
required artifacts *together*.

This skill follows the [check-skill
pattern](../../_shared/references/check-skill-pattern.md). Tier-1 +
Tier-3 detection is in
[`scripts/audit_pair.py`](scripts/audit_pair.py) (10 `rule_id`s; emits
a JSON array of envelopes via `_common.py`). Tier-2 has one judgment
dimension at
[`references/check-brief-content-quality.md`](references/check-brief-content-quality.md)
(read inline by the primary agent during evaluation).

`<SKILL_ROOT>` and `<SHARED_REF_DIR>` resolve from the chosen target —
see [skill-locations.md](../../_shared/references/skill-locations.md)
for the prefix table.

## When to use

Also fires when the user phrases the request as:

- "check pair integrity"
- "is this pair consistent"

## Workflow

### 1. Scope

Parse `$ARGUMENTS` as the primitive name (kebab-case, no path
prefix). Refuse on empty input — this skill operates on a named
primitive, not a configuration. Confirm scope aloud in one line:
`Auditing skill-pair for primitive: <name>`.

The four required artifact slots `audit_pair.py` inspects:

- Principles doc: `<SHARED_REF_DIR>/<name>-best-practices.md`
- Build skill: `<SKILL_ROOT>/build-<name>/SKILL.md`
- Check skill: `<SKILL_ROOT>/check-<name>/SKILL.md`
- Routing registration: `<SHARED_REF_DIR>/primitive-routing.md`
  (both route lines; required for `plugin` target, optional otherwise)

Plus the optional brief: `.briefs/<name>.brief.md` (warn-level;
content quality judged in Tier-2).

### 2. Target

Pick the placement scope before invoking the script. If `$ARGUMENTS`
includes `--target <plugin|project|user>`, use it. Otherwise apply
the inference rule from
[skill-locations.md](../../_shared/references/skill-locations.md):
walk up CWD for a plugin source tree, then for a project `.claude/`
directory, falling back to `user`. Surface the inferred target in
one line and confirm before invoking the script.

### 3. Tier-1 + Tier-3 Deterministic Checks

Execute the deterministic audit, passing the resolved target:

```bash
python3 plugins/build/skills/check-skill-pair/scripts/audit_pair.py \
  --target <plugin|project|user> <name>
```

The script emits a **JSON array of 10 envelopes** to stdout. Each
envelope:

```json
{
  "rule_id": "<rule>",
  "overall_status": "pass" | "warn" | "fail" | "inapplicable",
  "findings": [
    {
      "status": "warn" | "fail",
      "location": {"line": int, "context": str} | null,
      "reasoning": "<≤2 sentences>",
      "recommended_changes": "<canonical repair recipe>"
    }
  ]
}
```

`recommended_changes` is canonical — copy it through to the report;
do not paraphrase.

**Rule set** (10 rules):

| Tier | rule_id | Severity |
|---|---|---|
| 1 | `principles-doc-presence` | fail |
| 1 | `build-skill-presence` | fail |
| 1 | `check-skill-presence` | fail |
| 1 | `check-rule-files-presence` | fail |
| 1 | `routing-registration-presence` | fail (plugin target) / warn (project, user) |
| 1 | `brief-presence` | warn |
| 2 | `principles-doc-structure` | warn |
| 3 | `shared-principles-path` | fail |
| 3 | `check-half-references-principles-doc` | warn |
| 3 | `build-to-check-handoff` | warn |

Exit codes: `0` if no envelope is `fail`; `1` if any envelope is
`fail`; `64` on argument error.

**No-pair-found behavior.** When `principles_doc` + both SKILLs are
all missing, the 3 presence rules emit `fail` envelopes; the other
7 envelopes emit `overall_status: inapplicable` (the audit cannot
read what doesn't exist). Surface this case explicitly: "No pair
found for `<name>` — recommend `/build:build-skill-pair <name>`".
There is nothing else to audit.

### 4. Tier-2 — Brief content quality (judgment)

If `brief-presence`'s envelope is `pass` (or `warn` only for sections
missing — the brief itself exists), evaluate it against
[`references/check-brief-content-quality.md`](references/check-brief-content-quality.md).

Skip this Tier when the brief is absent entirely — Tier-1 already
flagged it and there is nothing to read.

#### Evaluator policy

- **Single locked-rubric pass.** Read `check-brief-content-quality.md`
  first, then evaluate the brief's prose against the unified rubric. A
  single locked-rubric pass produces stable scoring.
- **Default-closed when borderline.** When evidence is ambiguous,
  return `warn`, not `pass`.
- **Severity floor: WARN.** Brief content quality is coaching, not
  blocking — the build still works; the trace just leaks intent.
- **One finding maximum.** If both *So-what* and *Scope boundaries*
  fail, surface the higher-signal one with concrete excerpts.

### 5. Report

Merge the Tier-1/3 JSON envelopes and the Tier-2 judgment finding (if
any) into a unified findings table:

```
| Tier | rule_id | Artifact | Status | Reasoning |
|------|---------|----------|--------|-----------|
```

Sort: `fail` before `warn` before `inapplicable`; within severity,
Tier-1 before Tier-2 before Tier-3. Summary line at top and bottom:
`N fail, N warn, N inapplicable across 4 artifact slots`. If any
envelope is `fail` and excludes downstream tiers (the no-pair case),
name the trigger.

For each finding's `Recommendation:` line, copy the
`recommended_changes` field through verbatim. Multi-paragraph recipes
condense to the first paragraph in the report; full recipe in the
opt-in repair loop.

### 6. Opt-In Repair Loop

Ask exactly once:

> "Apply fixes? Enter `y` (all), `n` (skip), or comma-separated
> numbers."

For each selected finding, route per the recipe in
`recommended_changes`:

- **Direct edit** — routing-doc registration (write missing route
  lines), check half's principles-doc reference (add to
  `references:`), build→check handoff wording. Show the diff; write
  on confirmation.
- **Routed to another skill** — missing principles doc or large-scale
  pair damage → recommend `/build:build-skill-pair <name>` to
  rebuild from input material; missing brief → ask whether to author
  a retroactive brief inline or route to the meta-skill.
- **Tier-2 brief content quality** — ask the user to name the
  specific gap / user / problem (for *So-what*), or list concrete
  in/out items (for *Scope boundaries*). Rewrite the section; show
  the diff; write on confirmation.

After each applied fix, re-run `audit_pair.py` (or re-judge
Tier-2) on the affected scope so subsequent findings reflect the new
state. Terminate the loop when the user selects no further findings,
enters `n`, or confirms `done`.

## Anti-Pattern Guards

1. **Auditing a single SKILL.md.** The pair is the unit of work
   here. Per-SKILL.md concerns — description routing quality,
   frontmatter shape, body length, ALL-CAPS density — belong to
   `/build:check-skill`.
2. **Re-implementing structural pattern compliance.**
   `check-skill-pattern.md` is the canonical pattern doc;
   `check_skill_pattern.py` is the canonical structural auditor. This
   skill audits *pair-level* integrity (cross-half drift, pair
   registration, principles-doc presence), not *per-half* pattern
   compliance. If you find yourself wanting to add "is this check
   half pattern-compliant" rules here, run `check_skill_pattern.py`
   against each half instead — duplication for compliance is the
   wrong tradeoff.
3. **Bulk-applying fixes.** Per-finding confirmation is required.
   Pair-integrity findings are often intentional mid-refactor states
   (a dimension in flight, a principles doc being rewritten), and
   bulk-applying "fixes" overwrites deliberate work.
4. **Auditing principles-doc prose quality.** This skill checks
   *structural* integrity — required H2 sections present, halves
   reference the same path — not pattern-level critique. Quality
   concerns about the distilled rubric are a
   `/build:build-skill-pair` re-run, not an audit task.
5. **Skipping Tier-1 when Tier-2 looks juicy.** Missing artifacts
   are the load-bearing finding. Tier-2 brief content quality reads
   nothing if the brief is absent — running it produces cascading
   misses.
6. **Re-evaluating Tier-1 rules in Tier-2.** Scripts are authoritative
   for the 10 rules they cover; trust a `pass` envelope.
7. **Suppressing the inapplicable envelope.** When no pair is found,
   the 7 dependent envelopes emit `inapplicable` — that is the
   user's signal that the audit couldn't read what doesn't exist.
   Surfacing it is the contract; hiding it silently under-audits.
8. **Embellishing scripts' `recommended_changes`.** Each rule's
   recipe constant is canonical guidance sourced from
   `skill-pair-best-practices.md`. Copy it through; do not paraphrase
   or expand.

## Key Instructions

- Won't audit a single SKILL.md — the pair is the unit. Route to
  `/build:check-skill` for per-SKILL.md quality. Route to
  `plugins/build/_shared/scripts/check_skill_pattern.py` for per-half
  structural pattern compliance.
- Won't apply fixes without per-finding confirmation. The Repair
  Loop is opt-in and per-item.
- Tier-1 + Tier-3 deterministic checks are delegated to
  `scripts/audit_pair.py` — 10 `rule_id`s. The SKILL body only adds
  the `check-brief-content-quality` judgment pass (Tier-2) on top.
- When the primitive has no artifacts at all (principles_doc + both
  SKILLs all missing), the 3 presence rules emit `fail`; the other 7
  envelopes emit `inapplicable`. Surface this as "No pair found for
  `<name>`" and recommend `/build:build-skill-pair <name>`. There is
  nothing else to audit.
- Recovery: this skill is read-only outside the Repair Loop. Edits
  produced can be reverted via `git diff` / `git checkout`; the skill
  itself performs no destructive actions.

## Handoff

**Chainable to:** `/build:check-skill` (to audit each half's
per-SKILL.md quality once structural integrity is clean);
`/build:build-skill-pair` (to rebuild when the principles doc is
missing or structurally incomplete);
`plugins/build/_shared/scripts/check_skill_pattern.py` (per-half
structural pattern compliance — separate from this skill's pair-level
integrity check).
