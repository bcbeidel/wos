# Research Skill Enhancement Implementation Plan

**Goal:** Add Challenge phase, search protocol logging, and confidence levels to the `/wos:research` skill (Issue #39)

**Architecture:** New `wos/research_protocol.py` module provides mechanical search protocol logging (2 dataclasses + 2 formatters + CLI). Three new/rewritten skill reference files restructure the workflow from 7 to 6 phases, adding a Challenge gate between evaluation and synthesis. Existing reference files (SIFT, source evaluation, source verification) are unchanged.

**Tech Stack:** Python 3.9, pytest, dataclasses, argparse, json

**Branch:** `feat/research-skill-enhancement`
**Issue:** #39
**PR:** https://github.com/bcbeidel/wos/pull/49

---

## Task 1: SearchEntry and SearchProtocol Dataclasses

**Files:**
- Create: `wos/research_protocol.py`
- Create: `tests/test_research_protocol.py`

- [x] Write failing tests for dataclasses (5 tests)
- [x] Run tests to verify they fail (ImportError)
- [x] Implement `SearchEntry` and `SearchProtocol` dataclasses
- [x] Run tests to verify they pass (5 pass)
- [x] Commit: `feat: add SearchEntry and SearchProtocol dataclasses`

---

## Task 2: format_protocol() Markdown Table Renderer

**Files:**
- Modify: `wos/research_protocol.py`
- Modify: `tests/test_research_protocol.py`

- [x] Write failing tests for format_protocol (5 tests)
- [x] Run tests to verify they fail (ImportError)
- [x] Implement `format_protocol()`
- [x] Run tests to verify they pass (10 pass)
- [x] Commit: `feat: add format_protocol() markdown table renderer`

---

## Task 3: format_protocol_summary() One-Line Summary

**Files:**
- Modify: `wos/research_protocol.py`
- Modify: `tests/test_research_protocol.py`

- [x] Write failing tests for format_protocol_summary (3 tests)
- [x] Run tests to verify they fail (ImportError)
- [x] Implement `format_protocol_summary()`
- [x] Run tests to verify they pass (13 pass)
- [x] Commit: `feat: add format_protocol_summary() one-line summary`

---

## Task 4: CLI Entry Point

**Files:**
- Modify: `wos/research_protocol.py`
- Modify: `tests/test_research_protocol.py`

- [x] Write failing tests for CLI (3 JSON parser tests + 3 CLI tests)
- [x] Run tests to verify they fail (ImportError)
- [x] Implement `_protocol_from_json()`, `main()`, and `__main__` block
- [x] Run tests to verify they pass (19 pass)
- [x] Verify CLI end-to-end
- [x] Commit: `feat: add CLI entry point for research protocol formatting`

---

## Task 5: Challenge Phase Reference Document

**Files:**
- Create: `skills/research/references/challenge-phase.md`

- [x] Create challenge-phase.md (3 sub-steps: Assumptions Check, ACH, Premortem)
- [x] Commit: `docs: add challenge phase reference for research skill`

---

## Task 6: Rewrite Workflow as 6 Phases

**Files:**
- Remove: `skills/research/references/research-investigate.md`
- Create: `skills/research/references/research-workflow.md`

- [x] Create research-workflow.md (6 phases with search protocol + confidence levels)
- [x] Remove old research-investigate.md
- [x] Commit: `docs: replace 7-phase workflow with 6-phase research workflow`

---

## Task 7: Add Challenge Column to Mode Matrix

**Files:**
- Modify: `skills/research/references/research-modes.md`

- [x] Add Challenge column to mode matrix table (Full/Partial per mode)
- [x] Add Challenge Sub-Steps by Mode section (Assumptions/ACH/Premortem)
- [x] Commit: `docs: add Challenge column and sub-step matrix to research modes`

---

## Task 8: Update SKILL.md

**Files:**
- Modify: `skills/research/SKILL.md`

- [x] Change workflow reference from `research-investigate.md` to `research-workflow.md`
- [x] Add 3 new key rules (Challenge before synthesis, Log search protocol, Confidence levels)
- [x] Commit: `docs: update SKILL.md with new workflow reference and key rules`

---

## Task 9: Full Verification Pass

- [x] Run full test suite: 110 passed
- [x] Linter: ruff not installed locally (CI handles it)
- [x] CLI end-to-end: format + --summary verified
- [x] All 7 required skill files exist
- [x] Old research-investigate.md removed
- [x] No stale references in SKILL.md
- [x] Push branch and create PR: https://github.com/bcbeidel/wos/pull/49
