---
name: Research Skill Fixes Design
description: Design for addressing GitHub issues #52-55 (research skill bugs and DX improvements)
type: plan
related:
  - skills/research/SKILL.md
  - skills/research/references/research-workflow.md
  - wos/research_protocol.py
  - scripts/audit.py
---

# Research Skill Fixes Design

**Issues:** #52, #53, #54, #55
**Approach:** Minimal targeted fixes + protocol input validation
**Branch:** TBD
**PR:** TBD

## Context

Four open issues report friction in the research skill, spanning a bug, DX
gaps, and missing guidance. All stem from documentation/code mismatches rather
than fundamental architectural problems.

## Design Decisions

1. **`not_searched` stays `List[str]`** — simpler than objects, docs align to code
2. **Quality gate uses `scripts/validate.py`** — not `parse_document()`, because
   `validate_file()` already runs research-specific checks
3. **CLI entry points only** — no PYTHONPATH changes, follows existing `scripts/` pattern
4. **Guidance is additive** — new callout sections in the workflow, no structural changes

## Changes

### Issue #52: `not_searched` format mismatch (bug)

**Files:** `research-workflow.md`, `wos/research_protocol.py`

- Update all `not_searched` examples in the workflow to show `List[str]` format:
  ```json
  "not_searched": [
    "Google Scholar - covered by direct source fetching",
    "PubMed - topic is not biomedical"
  ]
  ```
- Add input validation in `_protocol_from_json()`: if any entry in `not_searched`
  is not a string, raise `ValueError` with a clear message explaining the
  expected format.

### Issue #53: DX for Python utilities (enhancement)

**Files:** `scripts/validate.py` (new), `skills/research/references/python-utilities.md` (new), `research-workflow.md`

- **`scripts/validate.py`** — thin CLI entry point for single-file validation:
  ```
  python3 scripts/validate.py <file> [--root DIR] [--no-urls]
  ```
  Calls `validate_file()`, prints issues or "All checks passed." Exits 1 on
  failure. Same deferred-import pattern as `audit.py`.

- **`python-utilities.md`** — reference doc documenting all CLI commands used
  during research:
  - `python3 scripts/validate.py <file>` — single file validation
  - `python3 scripts/audit.py --root <dir>` — project validation
  - `echo '<json>' | python3 -m wos.research_protocol format` — protocol table
  - `echo '<json>' | python3 -m wos.research_protocol format --summary` — one-liner
  - Full search protocol JSON schema with examples
  - `Document` dataclass field reference

### Issue #54: Research quality gate (enhancement)

**Files:** `research-workflow.md`

- Update Phase 6 quality checklist: replace `parse_document()` reference with
  `python3 scripts/validate.py <file>`. This runs all 4 checks (frontmatter,
  research sources, source URLs, related paths).

### Issue #55: Fetch failure guidance (enhancement)

**Files:** `research-workflow.md`

- **Phase 2 (Gather):** Add "Handling fetch failures" callout covering
  cascading parallel WebFetch failures, 403/301/timeout handling, and the
  principle that fetch failure alone doesn't invalidate a source.

- **Phase 1 (Frame):** Add "Source diversity" callout acknowledging WebSearch
  routes through one engine, with workarounds (vary queries, fetch known
  database URLs directly, log honestly).

## Testing

- Existing tests for `research_protocol.py` must still pass
- Add test for `_protocol_from_json()` rejecting non-string `not_searched` entries
- Add tests for new `scripts/validate.py` CLI
- Manual verification: run the research workflow and confirm updated docs are
  clear and actionable

## Non-goals

- Changing `parse_document()` signature or behavior
- Adding retry logic to `url_checker.py`
- Building integrations with academic databases
- Changing the `SearchProtocol` dataclass structure
