---
name: Skill Chain Design and Audit
description: One skill (audit-chain) and a lint extension for designing, documenting, and validating Claude Code skill chains — audit-chain is a repair loop that produces a chain manifest, cross-references it against SKILL.md files, and fixes gaps. Lint auto-detects chain manifests for structural checks.
type: design
status: superseded
related:
  - docs/context/skill-handoff-contracts-and-state-design.context.md
  - docs/context/skill-chain-failure-modes-and-antipatterns.context.md
  - docs/context/skill-chain-sequential-and-recursive-design-rules.context.md
  - docs/context/skill-chain-hitl-patterns-and-cli-translation-gap.context.md
  - docs/context/skill-chain-handoff-signaling-and-evidence-packs.context.md
  - docs/research/2026-04-10-skill-chaining-best-practices.research.md
  - docs/research/2026-04-10-skill-effectiveness-audit.research.md
  - docs/plans/2026-04-09-wiki-structural-refactor.plan.md
---

> **Superseded.** This design was drafted with `design-chain` and `check-chain` as two separate skills. The 2026-04-10 design session merged them into a single **`audit-chain`** repair loop. Implementation is tracked in:
> - #224 — chain manifest format + `wos/chain.py` structural validators
> - #225 — `/wos:audit-chain` repair loop skill
>
> **Key design change:** `audit-chain` is not just a linter — it's a repair loop. After identifying gaps (structural + LLM cross-reference), it proposes fixes and invokes `/wos:build-skill` inline for missing skills. The linter role (structural checks only) is handled by `scripts/lint.py` auto-detection.

# Skill Chain Design and Audit

One skill (`audit-chain`) and a lint extension that bring design discipline to
Claude Code skill chains. The chain manifest (`*.chain.md`) is the central
artifact — a human-readable specification documenting skill sequence, handoff
contracts, and gate points.

## Purpose

Most skill chain failures are structural design failures, not prompt failures.
The highest-leverage intervention is declaring output contracts before writing
skills. `audit-chain` makes this discipline tractable: it forces explicit
contract declaration at design time, verifies contracts against reality, and
repairs gaps inline.

## Behavior

### `audit-chain` (single skill — repair loop)

**When invoked with a workflow goal (no existing manifest):**

1. Takes a user-described workflow goal as free-text input
2. Discovers available SKILL.md files across the project and any installed plugins
3. Through structured dialogue: establishes skill sequence, elicits output contract per skill, declares input requirements, identifies human gate points, declares termination condition and negative scope
4. Produces `plans/YYYY-MM-DD-<name>.chain.md`
5. Hard gate: design only at this stage

**When invoked with an existing manifest:**

1. **Structural check** — each declared skill exists; handoffs consistent; no cycles (fast fail, from `wos/chain.py`)
2. **Cross-reference** — reads each SKILL.md body; LLM judgment on whether declared output contracts are plausible
3. **Repair** — for each mismatch, proposes fix; applies on per-change user confirmation
4. If gap requires a new skill: invokes `/wos:build-skill` inline
5. **Re-verify** — re-runs structural + cross-reference checks after repairs
6. Repeat until clean or user exits

### `lint` extension

Auto-detects `*.chain.md` files. When found, runs `wos/chain.py` structural
validators (existence, consistency, gates, termination, cycles). No new flag.
Structural checks only — no LLM judgment in `scripts/lint.py`.

## Components

**New skill:**
- `skills/audit-chain/SKILL.md` (replaces the original `design-chain` + `check-chain` pair)

**New Python module:**
- `wos/chain.py` — structural validators:
  - `parse_chain(manifest_path)` — reads and parses a `*.chain.md` manifest
  - `check_chain_skills_exist(manifest, skills_dirs)` — each declared skill exists
  - `check_chain_internal_consistency(manifest)` — handoff outputs match inputs
  - `check_chain_gates(manifest)` — gate points present before consequential steps
  - `check_chain_termination(manifest)` — termination condition declared
  - `check_chain_cycles(manifest)` — no circular skill references
- `tests/test_chain.py`

**Modified:**
- `wos/validators.py` — add `validate_chain(manifest_path, skills_dirs)`
- `scripts/lint.py` — auto-detect `*.chain.md`; call `validate_chain()` when found
- `tests/test_lint.py` — chain auto-detection tests

**New file type:**
`*.chain.md` — lives in `plans/`. Chain-level: name, goal, termination condition, negative scope. Per-skill: which skill, output contract, input contract, gate type.

## Constraints

- Does not modify anything without per-change user confirmation
- Structural checks before LLM cross-referencing (fast fail first)
- Works on SKILL.md files from any source
- Partial manifests produce findings, not errors
- `scripts/lint.py` extension: structural only, no LLM judgment, additive

## Acceptance Criteria

1. User with a workflow goal runs `/wos:audit-chain` → receives a `*.chain.md` manifest
2. `/wos:audit-chain` against a manifest with undeclared output contracts → specific finding per missing contract
3. Repair loop applies a fix and re-verifies without requiring the user to re-invoke
4. `scripts/lint.py` on a project with `*.chain.md` includes structural findings
5. `scripts/lint.py` on a project without `*.chain.md` — identical to before
6. `from wos.chain import parse_chain, check_chain_skills_exist, check_chain_internal_consistency, check_chain_gates, check_chain_termination, check_chain_cycles` imports cleanly
