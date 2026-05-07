# Changelog

## 0.2.3

- Cycle 4 process-echo guard sweep: drop guards whose body paraphrases
  a numbered workflow step or restates a Key Instruction. Eight guard
  bullets removed across three skills:
  - `scope-work` (Premature convergence + Over-specification +
    Single-option proposal; 6 → 3 guards)
  - `verify-work` (Validating with unchecked tasks + Marking completed
    on failure + Inventing criteria; 6 → 3 guards)
  - `plan-work` (Premature implementation + Skipping the infeasibility
    check; 7 → 5 guards)
- Each retained guard names a primitive-specific failure mode the
  workflow steps cannot prevent on their own. Several retained guards
  cite a step number incidentally as routing shorthand — kept per the
  exception clause in
  `_shared/references/skill-best-practices.md` (Authoring Principles
  → Anti-Pattern Guards).

## 0.2.2

- Trigger-cap sweep: cap each SKILL.md description to ≤3 quoted phrases;
  surplus phrases relocated to `## When to use` (#429, refs #399).
  Touches `finish-work`, `scope-work`, `start-work`, and `verify-work`
  skill descriptions.
