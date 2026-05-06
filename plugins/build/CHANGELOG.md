# Changelog

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
