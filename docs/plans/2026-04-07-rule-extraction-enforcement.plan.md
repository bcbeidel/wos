---
name: Rule Extraction and Enforcement
description: Implement LLM-driven extract-rules and check-rules skills with rule templates and hook guidance
type: plan
status: executing
branch: rule-extraction-enforcement
related:
  - docs/designs/2026-04-07-rule-extraction-enforcement.design.md
  - docs/research/2026-04-07-effective-rules-for-llm-enforcement.research.md
---

## Goal

Add a rule extraction and enforcement system to WOS. Users capture codebase
conventions as structured markdown rule files in `docs/rules/` and enforce
them via LLM-based semantic evaluation — on-demand with `/wos:check-rules`
or optionally via Claude Code hooks. A companion `/wos:extract-rules` skill
helps create well-formed rules from conversations, exemplary code, or
external sources. A starter template library provides common rules.

## Scope

**Must have:**

- `/wos:extract-rules` skill with three source modes
- `/wos:check-rules` skill with research-informed evaluation prompt
- Rule format guide (reference document)
- Evaluation prompt template (reference document)
- 5-8 rule templates organized by concern
- Hook setup guidance (reference document, positioned as optional)

**Won't have:**

- Python module changes (no Document model, validators, discovery, or scripts)
- Deterministic rule matching (Claude handles scope matching in-conversation)
- Rule versioning or changelog
- Cross-file rules
- Auto-fix / remediation suggestions
- CI integration

**Future (when concept is validated):**

- Extract deterministic parts (discovery, scope matching) into Python
- Add rule format validation to `validators.py`
- Add `scope`/`severity` fields to Document dataclass

## Approach

Skills-first: both skills are pure SKILL.md files with reference documents.
No Python changes. Claude reads `docs/rules/`, reads target files, does
scope matching and compliance evaluation entirely in-conversation.

This follows the WOS principle "Structure in code, quality in skills" —
start with quality in skills, add structure in code when the rule format
and workflow are validated through use.

Rule files are plain markdown with a known frontmatter convention (name,
description, type, scope, severity). The existing frontmatter parser
already handles these fields — no code changes needed for Claude to
read and understand them.

Templates live in `skills/extract-rules/templates/` and get copied to
the user's `docs/rules/` on adoption.

## File Changes

### Create

| File | Purpose |
|------|---------|
| `skills/extract-rules/SKILL.md` | Extract-rules skill with three modes |
| `skills/extract-rules/references/rule-format-guide.md` | Rule format specification and writing guidelines |
| `skills/extract-rules/templates/*.rule.md` | 5-8 starter rule templates |
| `skills/check-rules/SKILL.md` | Check-rules skill with evaluation prompt |
| `skills/check-rules/references/evaluation-prompt.md` | Research-informed evaluation prompt template |
| `skills/check-rules/references/hook-setup.md` | Optional hook configuration guidance |

### No changes

- No modifications to any Python files
- No new tests (skills are validated by audit and manual use)

## Tasks

- [x] **Task 1: Create extract-rules SKILL.md.** <!-- sha:0914413 -->
  Skill with three extraction modes:
  - From conversation: ask clarifying questions (scope, severity, examples),
    write rule file to `docs/rules/`
  - From code: read exemplary files, infer the convention, propose a rule
    with examples drawn from actual code
  - From external source: distill enforceable rules from provided docs,
    present candidates for user selection
  All modes: propose rule for user approval before writing, generate both
  compliant and non-compliant examples (non-compliant first per research),
  default severity to `warn`, check for duplicates in `docs/rules/`.
  Verify: skill appears in Claude Code skill list; SKILL.md passes
  `python scripts/audit.py --root . --no-urls` with no new failures.

- [x] **Task 2: Create rule format guide reference.** <!-- sha:bc84060 -->
  `skills/extract-rules/references/rule-format-guide.md` covering:
  - Complete rule file format with all frontmatter fields
  - Full example of a well-formed rule file
  - Guidelines for writing effective intent sections (why > what)
  - Guidelines for writing effective examples (non-compliant first,
    concrete anchors, drawn from real code when possible)
  - Scope pattern examples (single glob, list of globs)
  - Severity guidance (default `warn`, use `fail` for hard constraints)
  Verify: file exists with valid frontmatter.

- [x] **Task 3: Create check-rules SKILL.md.** <!-- sha:8928012 -->
  Skill that:
  - Reads all rule files from `docs/rules/` (glob for `*.rule.md`)
  - Accepts optional target: specific files, directory, or defaults to
    git-changed files (`git diff --name-only`)
  - For each rule, matches scope glob against target files
  - For each matched rule×file pair, reads the rule file verbatim and
    the target file, evaluates compliance using the evaluation prompt
    from `references/evaluation-prompt.md`
  - Reports results in the design's output format:
    `PASS  <file> — <rule-name>` / `FAIL  <file> — <rule-name>` with
    explanation
  Verify: skill appears in Claude Code skill list; SKILL.md passes audit.

- [x] **Task 4: Create evaluation prompt reference.** <!-- sha:5a96c6f -->
  `skills/check-rules/references/evaluation-prompt.md` — the
  research-informed evaluation prompt template:
  - Full rule file included verbatim (locked rubric pattern [15])
  - Chain-of-thought reasoning required before verdict [3, 16]
  - Binary PASS/FAIL output with explanation [11, 17]
  - Edge case handling (empty files, binary files, files outside scope)
  - Instruction to evaluate one rule against one file at a time [12]
  Verify: file exists with valid frontmatter.

- [x] **Task 5: Create 5-8 rule templates.** <!-- sha:45c095c -->
  Place in `skills/extract-rules/templates/`. Each template is a complete
  rule file with frontmatter, intent, and examples. Templates use generic
  scope patterns that users customize for their project.
  Categories to cover (pick 5-8):
  - Layer boundaries (no business logic in data access / staging layer)
  - Naming conventions (test files mirror source file names)
  - Documentation requirements (public modules need docstrings)
  - Code organization (no circular imports between packages)
  - Test requirements (new modules require corresponding test files)
  - API design (endpoints validate input before processing)
  - Configuration (no hardcoded secrets or credentials)
  - Data pipeline (staging models only cast, rename, deduplicate)
  Verify: each template has valid frontmatter with name, description,
  type, scope, and severity fields.

- [ ] **Task 6: Create hook setup reference and update indexes.**
  `skills/check-rules/references/hook-setup.md` covering:
  - How to wire check-rules into Claude Code `settings.json` as a hook
  - Example hook configuration for pre-commit
  - Guidance: start on-demand, graduate to hooks when rule quality is
    trusted; recommend hooking only `fail`-severity rules
  Then run `python scripts/reindex.py --root .` to update indexes.
  Verify: `python scripts/audit.py --root . --no-urls` shows no new
  index-sync or skill-related failures.

## Validation

1. **Audit clean:** `python scripts/audit.py --root . --no-urls` produces
   no new failures related to skills or indexes.

2. **Skills registered:** Both `/wos:check-rules` and `/wos:extract-rules`
   appear in the Claude Code skill list.

3. **Templates well-formed:** All template rule files have valid
   frontmatter with required fields (name, description, type, scope,
   severity) and contain Intent and example sections.

4. **Existing tests pass:** `python -m pytest tests/ -v` — no regressions.
