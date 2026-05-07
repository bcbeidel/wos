# Changelog

## 0.23.0

- Repo simplification sweep cycles 1–3 (codify-then-sweep, per design
  `.designs/2026-05-07-simplification-sweep.design.md`):
  - **Cycle 1 (#432):** New Tier-1 detector
    `_shared/scripts/check_handoff_shape.py` flags `Receives:` /
    `Produces:` lines in any SKILL.md `## Handoff` section. Wired into
    `check-skill` Tier-1; codified in
    `skill-best-practices.md`. Sweep removed Receives/Produces
    boilerplate from ~55 SKILL.md across all 4 plugins.
  - **Cycle 2 (#433):** New Tier-1 detector
    `_shared/scripts/check_reference_lead.py` flags judgment-rule
    `references/*.md` files whose first body paragraph paraphrases the
    frontmatter `description:` (Jaccard token-overlap ≥ 0.70, stopwords
    excluded). Wired into `check-skill` Tier-1. Sweep dropped the
    leading restatement from 39 reference files.
  - **Cycle 3 (this release):** New Tier-1 detector
    `_shared/scripts/check_evaluator_policy_echo.py` flags SKILL.md
    files that copy the verbatim Evaluator-policy bullet triple from
    `check-skill-pattern.md` instead of citing the canonical SSoT
    (boolean AND across "Default-closed when borderline", "Severity
    floor: WARN", "One finding per dimension"). New Tier-2 dimension
    `check-skill/references/check-best-practices-doc-restatement.md`
    covers the broader pattern. The pattern doc itself flipped from
    "(copy verbatim)" to "(cite via anchor link)". Sweeps applied:
    Row 4 (12 check-* SKILL.md cite Evaluator policy by anchor),
    Row 7 (6 build-* SKILL.md drop generic "rm <path>" Recovery
    stanzas), Row 8 (7 build-* SKILL.md drop Won't bullets that
    echo frontmatter or Scope/Review-Gate steps), Row 18 (2 build-*
    SKILL.md collapse language-tiebreaker prose to a one-line link
    to `primitive-routing.md §Language Selection`).
  - Authoring rule "cite, don't restate, the principles doc" landed in
    both `skill-best-practices.md` and `skill-pair-best-practices.md`;
    `build-skill` and `build-skill-pair` scaffolder prose updated.

## 0.22.0

- Python script profiles (cli/library/skill-helper) for
  `build-python-script` and `check-python-script` (#430, refs #380 #389):
  - Profiles spec at `_shared/references/python-script-profiles.md` —
    canonical source for both halves of the pair.
  - `_shared/scripts/detect_python_profile.py` heuristic detector with
    `--profile=<name>` override (stdlib only, 9 unit tests).
  - `check-python-script` Tier-1 detectors: library-discipline
    (no-side-effects, public-api-declared) and skill-helper-contract
    (stdin-json, atomic-write, distinct-error-codes).
  - `check-python-script` Tier-2 dimensions: library
    (no-import-time-side-effects, public-symbols-typed,
    public-symbols-documented) and skill-helper
    (structured-stderr-errors, exit-code-meaning).
  - `build-python-script` Step 3 elicits profile up-front; Step 4 Draft
    branches on profile; Step 5 Safety Check adds Profile-fit group.
- Trigger-cap sweep: cap each SKILL.md description to ≤3 quoted phrases;
  surplus phrases relocated to `## When to use` (#429, refs #399). Adds
  `_shared/scripts/count_triggers.py` audit script. Touches every
  `build-*` and `check-*` skill description.

## 0.21.0

- Refactor every check-* skill onto the unified single-artifact-per-rule
  pattern — one rule per script or judgment reference, no co-mingled audits:
  - `check-bash-script` (#410)
  - `check-skill-chain` Manifest mode (#412)
  - `check-skill-pair` — Path B pair-integrity redefinition (#413)
  - `check-hook` — pure-judgment, 18 rules (#414)
  - `check-help-skill` — 17 scripted + 5 judgment + 1 cross-entity (#415)
  - `check-resolver` — 11 scripted + 4 judgment (#416)
  - `check-rule` — 9 scripted + 8 judgment + 1 cross-rule (#417)
  - `check-skill` — 21 scripted + 9 judgment + 1 cross-skill (#418)
  - `check-subagent` — 20 scripted + 7 judgment (#419)
  - `check-readme` — 28 scripted + 7 judgment + 1 cross-readme (#420)
  - `check-pre-commit-config` — 20 scripted + 7 judgment + 1 collision (#421)
  - `check-python-script` — 25 scripted + 9 judgment + 1 collision (#422)
  - `check-github-workflow` — 30 scripted + 7 judgment (#423)
  - `check-makefile` — 29 scripted + 7 judgment + 1 collision (#424)
- Add `check_skill_pattern.py` structural audit script for check-half
  compliance, used by `check-skill-pair` (#411)
- Add security-scan pre-commit hook with `check-skill` scanner integration
  (no LLM by default) (#403)
- Security cleanup — argparse refactor and defense-in-depth scanner notes
  (#402)
- Remove `check-skill-migration-template.md` after the sweep concluded

## 0.20.1

- Patch-bump for security cleanup
