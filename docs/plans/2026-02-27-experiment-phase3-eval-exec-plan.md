---
name: Experiment Phase 3 Eval+Exec Plan
description: >
  Implementation plan for Phase 3 of the experiment skill: Evaluation Design
  and Execution phase guidance, plus generate-manifest CLI command.
type: plan
related:
  - skills/experiment/SKILL.md
  - wos/experiment_state.py
  - scripts/experiment_state.py
---

# Experiment Phase 3: Evaluation & Execution

- **Branch:** `feat/77-experiment-eval-exec`
- **Issue:** #77
- **PR:** (pending)

## Tasks

- [x] Task 1: Add `generate_manifest()` function and `OPAQUE_IDS` constant to `wos/experiment_state.py` with 8 tests
- [x] Task 2: Add `generate-manifest` CLI subcommand to `scripts/experiment_state.py` with 3 tests
- [x] Task 3: Add Evaluation Phase guidance section to `skills/experiment/SKILL.md`
- [x] Task 4: Add Execution Phase guidance section to `skills/experiment/SKILL.md`
- [x] Task 5: Update Phase Routing table and Common Deviations in `skills/experiment/SKILL.md`

## Acceptance Criteria

- [x] `generate_manifest()` function works with tests
- [x] `generate-manifest` CLI subcommand works with tests
- [x] `uv run --extra dev pytest tests/ -v` passes (all existing + 11 new, 0 failures)
- [x] `uv run --extra dev ruff check .` clean
- [x] SKILL.md contains full Evaluation phase guidance with blinding matrix
- [x] SKILL.md contains full Execution phase guidance with opaque-ID enforcement
- [x] SKILL.md frontmatter parses correctly
- [x] All commits on a feature branch, ready for PR
