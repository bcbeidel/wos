---
name: Skill-Pair Best Practices
description: Authoring guide for a primitive-pair — a matched `build-<primitive>` + `check-<primitive>` pair sharing a distilled principles doc. The check half conforms to `check-skill-pattern.md` (single-artifact-per-rule discipline; Tier-1 scripts emit JSON envelopes with embedded recipes; Tier-2 judgment rules live as `references/check-*.md`). Referenced by build-skill-pair and check-skill-pair.
related:
  - plugins/build/_shared/references/check-skill-pattern.md
  - plugins/build/skills/build-bash-script/SKILL.md
  - plugins/build/skills/check-bash-script/SKILL.md
  - plugins/build/skills/build-python-script/SKILL.md
  - plugins/build/skills/check-python-script/SKILL.md
  - plugins/build/skills/build-skill-pair/SKILL.md
---

# Skill-Pair Best Practices

## What a Good Skill-Pair Does

A skill-pair is two skills authored as a unit: a scaffolder
(`build-<primitive>`) and an auditor (`check-<primitive>`) that share
a single distilled principles doc. Its value is that creation and
review never drift — both halves read from the same canonical
authority, so the patterns the scaffolder produces are the patterns
the auditor enforces. A pair earns its place when a primitive class
is introduced that (a) benefits from a scaffolding workflow, (b)
benefits from an audit workflow, and (c) carries enough convention
to distill into a rubric worth citing.

The pair is the unit. Either half alone is incomplete: a scaffold
without an audit produces artifacts nothing validates; an audit
without a scaffold enforces a rubric nothing produces. The
`build-skill-pair` meta-skill refuses to scaffold only one side for
this reason.

The check half conforms to the [check-skill
pattern](check-skill-pattern.md): single-artifact-per-rule,
Tier-1 detection scripts emitting JSON envelopes with embedded
`recommended_changes` recipes, Tier-2 judgment rules at
`references/check-*.md` read inline by the primary agent. Reading
that pattern doc before working on the check half is non-negotiable.

## Anatomy

Four required artifact slots form the pair (plus an optional
intent-trace brief). Each slot is load-bearing — missing any one
breaks a contract some other slot relies on.

```
plugins/build/
├── _shared/
│   └── references/
│       ├── <primitive>-best-practices.md        ← principles doc (rubric)
│       └── primitive-routing.md                 ← registration lives here
└── skills/
    ├── build-<primitive>/
    │   └── SKILL.md                             ← scaffolder; references principles
    └── check-<primitive>/
        ├── SKILL.md                             ← auditor; references principles + judgment rules
        ├── assets/
        │   └── output-example.json              ← canonical envelope shape
        ├── references/
        │   └── check-<rule>.md ...              ← one per judgment-mode rule
        └── scripts/
            ├── _common.py                       ← JSON-emit helpers
            ├── check_<rule>.{py,sh} ...         ← one per scripted rule (or one emitting an array)
            └── tests/
                ├── __init__.py
                └── test_common.py
```

The four required slots:

1. **Principles doc** — `_shared/references/<primitive>-best-practices.md`. The canonical "Why" for every rule the pair enforces. Both halves' `references[]` cite the same path. Required H2 sections: *What a Good <primitive> Does*, *Anatomy*, *Patterns That Work*, *Safety* (or *Safety & Maintenance*; both pass via prefix match). A separate *Anti-Patterns* section is encouraged but not required.
2. **Build half** — `build-<primitive>/SKILL.md`. The scaffolder.
3. **Check half** — `check-<primitive>/SKILL.md`. The auditor; structurally compliant with `check-skill-pattern.md` (Tier-1 / Tier-2 / Evaluator policy / `references[]` enumerates the judgment files + the principles doc).
4. **Routing registration** — `_shared/references/primitive-routing.md` carries both route lines (`/build:build-<primitive>` and `/build:check-<primitive>`).

The optional fifth slot:

- **Brief** — `.briefs/<primitive>.brief.md` captures intake intent. Briefs are throw-away — a missing brief is `warn`, not `fail`. When present, the *So-what* should name a specific gap / user / problem (judgment-evaluated by `check-brief-content-quality`).

The principles doc lives in `_shared/`, not inside either skill, so both halves cite the same absolute path. The check half's rules (judgment `.md` files and detection scripts) live with the check half because that is where they are applied. The routing-doc registration is the pair's public handle — without it, discovery is grep-only.

The check half's rule set is the union of `references/check-*.md` filenames + `rule_id`s emitted by `scripts/check_*.{py,sh}` outputs (per the single-artifact-per-rule discipline). Per-rule fix recipes are embedded as `_RECIPE_<NAME>` constants inside each detection script, sourced from the principles doc.

## Patterns That Work

- **Single shared principles doc.** Both halves' frontmatter `references:` resolve to the same path. Two docs (one per skill) guarantee drift; one doc makes drift impossible by construction.
- **Single-artifact-per-rule.** Every rule lives as exactly one of: a script (when ≥70% mechanically detectable) or a `references/check-<rule>.md` file (judgment-driven). Never both. Per `check-skill-pattern.md`.
- **Three-tier audit structure.** The check half organizes work as Tier-1 deterministic (scripts emit JSON envelopes) / Tier-2 judgment (primary agent reads `check-*.md` files inline) / Tier-3 cross-entity. Tier-1 short-circuits missing inputs so Tier-2/3 read nothing that is absent.
- **Embedded recipes.** Each detection script carries its own `_RECIPE_<NAME>` module-level constant sourced from the principles doc. Each judgment rule's *How to apply* section IS the recipe. Recipes live with the rule they serve, not in a separate document.
- **Per-finding Repair Loop.** The audit always offers an opt-in repair with per-item confirmation. Bulk application overwrites mid-refactor intent; per-finding keeps the user in control.
- **Scope Gate in the build half.** A scaffolder that forgets its scope produces out-of-bounds artifacts. Explicit refusal signals (wrong primitive, wrong language, setuid intent, etc.) at the top of the build workflow keep the pair honest.
- **Pair registered in `primitive-routing.md`.** Both route lines (`/build:build-<primitive>` and `/build:check-<primitive>`) appear, and the primitive class is described under *What Each Primitive Was Designed For* (new class) or *Language Selection* (variant).
- **SKILL.md cites the principles doc; it does not restate it.** When either half links to the principles doc (or to `check-skill-pattern.md` for the check half's Evaluator policy), the body emits a citation, not a copy. Verbatim duplicates of named principles drift on every edit; the Tier-1 helper `check_evaluator_policy_echo.py` and the Tier-2 dimension `check-best-practices-doc-restatement` flag the pattern.

## Anti-Patterns

- **Principles doc duplicated inside each skill.** The duplication creates two rubrics that diverge silently. Audit findings cite one copy while the scaffolder reads the other, and users discover the drift only when a pattern flagged in review was never in the scaffold template.
- **Rule lives as both a script AND a `check-*.md`.** The single-artifact-per-rule discipline forbids overlap. Pick one home: script if mechanically detectable at ≥70% recall, markdown otherwise.
- **Unregistered pair.** Pairs absent from `primitive-routing.md` are discoverable only by grep. Other skills and future authors do not find them; the pair sits on disk but is invisible to the routing layer that is supposed to catalog it.
- **Build without check (or vice versa) using this pattern.** Single-skill authoring has a home — `/build:build-skill` — and the pair pattern does not replace it. Scaffolding one half alone with the pair meta-skill produces a dangling rubric nothing references.
- **Scope Gate as a comment, not a refusal.** A build skill that documents wrong-primitive cases but does not *refuse* them lets misrouted scaffolds through. The Gate's authority is in the refuse; the language is secondary.
- **Force-fitting the pattern when it doesn't apply.** Hybrid skills (design+audit, like `check-skill-chain`) invoke the **design+audit hybrid carve-out** in `check-skill-pattern.md`. Cross-plugin tool delegation at Tier-1 (e.g., `wiki/lint.py`) is allowed and documented; do not wrap it in a thin local script just to satisfy "scripts/check_*.* owned by this skill" — duplication for compliance is the wrong tradeoff.

## Safety & Maintenance

**Evolving a pair.** Update the principles doc first, then the per-rule files (refactor existing detection scripts' `_RECIPE_*` constants; add or modify judgment `check-*.md` files), then both SKILL bodies to cite any newly-named workflow step. Landing these in reverse order — SKILLs first — produces a window where the body claims patterns the rule files do not yet carry.

**Retiring a pair.** Delete in reverse-dependency order: SKILL bodies first, then per-rule files (`check-*.md`, `scripts/check_*.*`, `_common.py`), then the principles doc, then the routing-doc lines. Running `/build:check-skill-pair <name>` after deletion should return `No pair found for <name>` cleanly.

**Version discipline.** A pair is a single shipping unit; both halves ship together or neither does. The build plugin's version bump covers the whole pair — no partial-pair releases.

**Auditing the pair's own integrity.** `/build:check-skill-pair <name>` walks the four required slots, surfaces drift (missing principles doc, divergent principles paths between halves, missing routing registration, build half not citing the check half), and delegates structural pattern compliance of the check half to `plugins/build/_shared/scripts/check_skill_pattern.py`. Run it after any pair-spanning change.
