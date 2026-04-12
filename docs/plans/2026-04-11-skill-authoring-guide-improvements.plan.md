---
name: Skill Authoring Guide Improvements
description: Apply nine progressive-disclosure and cross-platform findings from the skill curation comparative analysis to skill-authoring-guide.md
type: plan
status: approved
branch: skill-curation-comparative-analysis
pr: TBD
related:
  - docs/research/2026-04-11-skill-curation-comparative-analysis.research.md
  - skills/lint/references/skill-authoring-guide.md
---

# Skill Authoring Guide Improvements

**Goal:** Apply nine targeted improvements to `skills/lint/references/skill-authoring-guide.md` — the rubric used by `/wos:lint` to evaluate skill quality — drawn from gaps G4, G5, G7, G9, G10, G12, G13 identified in the skill curation comparative analysis, plus L2/L3 content placement and L1 routing budget framing. The result is a guide that better explains progressive disclosure architecture, exposes runtime limits, documents portability tradeoffs, and makes the rationale-over-rigidity principle actionable.

**Scope:**

Must have:
- All nine changes applied to `skills/lint/references/skill-authoring-guide.md` exactly as specified
- One new row in the Judgment checks table (L2/L3 placement); automated checks table unchanged
- `python scripts/lint.py --root . --no-urls` — no new warnings or failures after changes

Won't have:
- Changes to `scripts/lint.py`
- Changes to any other file (SKILL.md files, context docs, check-skill, build-skill)
- New check-skill criteria (those are in separate plans)
- Reordering or removal of any existing section

**Approach:** Each task applies a logically related group of edits to the guide in document order, verifies with grep, runs lint, then commits. Tasks are sequential — each builds on the previous file state. All edits are additive: text is inserted after specified anchor locations with no removal of existing content.

**File Changes:**
- Modify: `skills/lint/references/skill-authoring-guide.md` (all nine changes)

**Branch:** `skill-curation-comparative-analysis`
**PR:** TBD

---

## Chunk 1: Description Section Enhancements

### Task 1: L1 routing budget framing + `tested_with` frontmatter + Trigger Evaluation subsection

Three additions that strengthen the description and frontmatter sections — the parts of the guide authors encounter first.

**Files:**
- Modify: `skills/lint/references/skill-authoring-guide.md`

**Change 9 — Reframe description as L1 routing budget:**
Strengthen the opening of the `### description (required)` subsection. Before the existing sentence "The most important field…", insert:

```
The description is the only content the model sees before deciding to trigger
the skill. It is the L1 routing signal — the entire routing decision happens
here. Nothing in the body contributes to routing. The effective routing window
is 250 characters (truncation in the skill listing), so trigger signal must
front-load.
```

**Change 3 — Add `tested_with` to optional frontmatter:**
After the closing ` ``` ` of the frontmatter YAML block (the block showing `name`, `description`, `argument-hint`, `user-invocable`, `references`), add a new paragraph:

```
`tested_with: [haiku, sonnet, opus]` — optional. Record of which models the
author verified against. More honest than a forward-looking min_model_tier
claim. Cross-tier skills should include at least one sub-frontier target.
Informs check-skill's directive density assessment.
```

**Change 5 — Add Trigger Evaluation subsection after Good/Bad examples:**
After the closing ` ``` ` of the "Bad" description example block, add:

```markdown
### Trigger Evaluation

**When routing is uncertain:** validate empirically. Generate 8–10 queries a
user would say to trigger this skill (should-trigger) and 8–10 near-miss
queries that should NOT trigger it. Test each against the live skill.
Calculate precision (correct activations / total activations) and recall
(correct activations / total should-trigger queries). Adjust the trigger
clause until both exceed 80%. Reference: Anthropic skill-creator `run_loop.py`
for a full automated implementation.
```

- [ ] **Step 1:** Read `skills/lint/references/skill-authoring-guide.md` in full to confirm anchor locations.
- [ ] **Step 2:** Apply Change 9 — insert L1 routing budget paragraph before "The most important field" in the `### description` subsection.
- [ ] **Step 3:** Apply Change 3 — add `tested_with` paragraph after the frontmatter YAML block.
- [ ] **Step 4:** Apply Change 5 — add `### Trigger Evaluation` subsection after the Bad description example block.
- [ ] **Step 5:** Verify: `grep -n "L1 routing signal" skills/lint/references/skill-authoring-guide.md` → line present; `grep -n "tested_with" skills/lint/references/skill-authoring-guide.md` → line present; `grep -n "Trigger Evaluation" skills/lint/references/skill-authoring-guide.md` → line present.
- [ ] **Step 6:** `python scripts/lint.py --root . --no-urls 2>&1 | grep "skill-authoring-guide"` → no new warnings.
- [ ] **Step 7:** Commit: `git commit -m "docs: add L1 routing budget framing, tested_with, and trigger evaluation to skill-authoring-guide"`

---

## Chunk 2: Loading Model + Body Enhancements

### Task 2: L2/L3 content placement rule + 30-skill session limit note

Two additions to the structural sections of the guide: the Loading Model explanation and the Size Limits subsection.

**Files:**
- Modify: `skills/lint/references/skill-authoring-guide.md`

**Change 1a — Add L2/L3 content placement rule below the Loading Model table:**
After the paragraph ending "…based entirely on the description. L3 loads only when SKILL.md references a file and the task needs it.", add:

```
L2 contains instructions — workflow steps, guards, decision rules. L3 contains
reference material — domain docs, schemas, lookup tables, long examples,
anything only needed in specific scenarios. The test: if a section of the body
would be skipped for most invocations, it belongs in L3. Embedding
reference-level material in the body bloats L2, defeats progressive disclosure,
and dilutes the routing signal by increasing body size without increasing
instruction density.
```

**Change 8 — Add 30-skill session limit note at end of Size Limits subsection:**
After the existing bullet "If approaching either limit, split content into reference files", add:

```
**Session limit:** Claude Code loads a maximum of 30 skills per session. In
projects exceeding this, skills beyond 30 are silently dropped from context
and routing to them fails without error. If your project approaches this limit,
use a meta-skill router: a single routing skill that dispatches to sub-skills
via keyword matching, counting as one toward the limit.
```

- [ ] **Step 1:** Read `skills/lint/references/skill-authoring-guide.md` to confirm the Loading Model paragraph ending and the Size Limits bullet text.
- [ ] **Step 2:** Apply Change 1a — insert L2/L3 content placement paragraph after the Loading Model closing paragraph.
- [ ] **Step 3:** Apply Change 8 — insert Session limit note after the Size Limits bullet.
- [ ] **Step 4:** Verify: `grep -n "L2 contains instructions" skills/lint/references/skill-authoring-guide.md` → line present; `grep -n "Session limit" skills/lint/references/skill-authoring-guide.md` → line present.
- [ ] **Step 5:** `python scripts/lint.py --root . --no-urls 2>&1 | grep "skill-authoring-guide"` → no new warnings.
- [ ] **Step 6:** Commit: `git commit -m "docs: add L2/L3 content placement rule and 30-skill session limit to skill-authoring-guide"`

---

## Chunk 3: Reference Files + Cross-Platform Portability

### Task 3: `assets/` subsection + Cross-Platform Portability section

Two additions that document the full directory model and portability tradeoffs.

**Files:**
- Modify: `skills/lint/references/skill-authoring-guide.md`

**Change 2 — Add `assets/` subsection after the Reference Files bullet list:**
After the existing `- File names should describe content: source-evaluation.md not ref2.md` bullet, add:

```markdown
### `assets/` (optional)

Output-bound files not loaded into context: templates, images, boilerplate
code, fonts, or any file used in skill output but not needed for reasoning.
Unlike `references/` (injected into context on demand), `assets/` files are
referenced in output paths but never consume context window tokens. Use when
the skill produces files and the source material should not be loaded. One
level deep from SKILL.md, same convention as `references/`.
```

**Change 6 — Add Cross-Platform Portability section after the Reference Files section:**
After the `assets/` subsection (or after the Reference Files section if no `assets/` section yet), add:

```markdown
## Cross-Platform Portability

The Agent Skills spec minimum (`name` + `description` + flat markdown body
fitting the initial context window) is confirmed portable across Claude Code
and GitHub Copilot CLI. Every WOS extension above that floor — `context: fork`,
`allowed-tools`, `references/` directories, `assets/` directories,
`!<command>` injection, `model`/`effort` — is Claude Code-specific and will
not function on other runtimes. Writing to the spec minimum forfeits dynamic
context injection, fork isolation, tool scoping, and progressive reference
loading — the features that make WOS skills structurally powerful. If
portability matters, author to the spec minimum and test on the target runtime.
```

- [ ] **Step 1:** Read `skills/lint/references/skill-authoring-guide.md` to confirm the Reference Files section's final bullet.
- [ ] **Step 2:** Apply Change 2 — add `### assets/ (optional)` subsection after the final Reference Files bullet.
- [ ] **Step 3:** Apply Change 6 — add `## Cross-Platform Portability` section after the Reference Files section (i.e., after the `assets/` subsection just added).
- [ ] **Step 4:** Verify: `grep -n "assets/" skills/lint/references/skill-authoring-guide.md` → subsection heading present; `grep -n "Cross-Platform Portability" skills/lint/references/skill-authoring-guide.md` → section heading present.
- [ ] **Step 5:** Confirm section order: Cross-Platform Portability appears after Reference Files and before Examples Beat Explanations (or wherever Examples currently sits) — check line numbers from grep output.
- [ ] **Step 6:** `python scripts/lint.py --root . --no-urls 2>&1 | grep "skill-authoring-guide"` → no new warnings.
- [ ] **Step 7:** Commit: `git commit -m "docs: add assets/ subsection and Cross-Platform Portability section to skill-authoring-guide"`

---

## Chunk 4: Evaluation Criteria Enhancements

### Task 4: Rationale transformation pattern + L2/L3 judgment row + Skill Lifecycle section

Three additions to the Evaluation Criteria section and a new section following it.

**Files:**
- Modify: `skills/lint/references/skill-authoring-guide.md`

**Change 4 — Update Rationale over rigidity judgment check row:**
In the Judgment checks table, find the row starting with `| Rationale over rigidity |` and update its "What to evaluate" cell to:

```
Does the skill explain *why* behind instructions, or rely on rigid ALL-CAPS directives (MUST, NEVER, ALWAYS)? Transformation pattern — Before: 'ALWAYS use markdown.' After: 'Use markdown — the user will review this output and markdown renders in the UI.' Convert directive → same behavior + reason why it matters. Explaining why produces smarter adaptation than compliance enforcement.
```

**Change 1b — Add L2/L3 placement row to Judgment checks table:**
After the final row in the Judgment checks table (`| Reference depth | Are all references one level deep from SKILL.md? |`), add:

```
| L2/L3 placement | Does the body contain domain docs, schemas, or lookup material that belongs in a named references/ file? |
```

**Change 7 — Add Skill Lifecycle and Staleness section after Evaluation Criteria:**
After the full Evaluation Criteria section (after the Judgment checks table), add:

```markdown
## Skill Lifecycle and Staleness

Skills are not static documents. Three triggers for review: (1) a framework,
API, or CLI tool referenced in the skill has changed version; (2) the skill
was verified against a model tier that is no longer default (see `tested_with`);
(3) a rule passes check-skill but is never followed in practice — confirm via
removal test. A stale rules file is actively harmful: it misleads agents toward
deprecated patterns with more authority than silence. Schedule a check-skill
audit at each major dependency upgrade. Optionally add a `reviewed:` date to
frontmatter after each audit.
```

- [ ] **Step 1:** Read `skills/lint/references/skill-authoring-guide.md` to confirm the Judgment checks table structure and final row.
- [ ] **Step 2:** Apply Change 4 — update the "Rationale over rigidity" row's "What to evaluate" cell with the transformation pattern.
- [ ] **Step 3:** Apply Change 1b — add L2/L3 placement row as the final row of the Judgment checks table.
- [ ] **Step 4:** Apply Change 7 — add `## Skill Lifecycle and Staleness` section after the Evaluation Criteria section.
- [ ] **Step 5:** Verify: `grep -n "Transformation pattern" skills/lint/references/skill-authoring-guide.md` → line present in Judgment table; `grep -n "L2/L3 placement" skills/lint/references/skill-authoring-guide.md` → table row present; `grep -n "Skill Lifecycle" skills/lint/references/skill-authoring-guide.md` → section heading present.
- [ ] **Step 6:** Confirm the Judgment table has exactly 11 rows (10 original + 1 new L2/L3 placement row) and the Automated table is unchanged: count rows with `grep -c "^|" skills/lint/references/skill-authoring-guide.md` and cross-check against pre-change count + 1.
- [ ] **Step 7:** `python scripts/lint.py --root . --no-urls 2>&1 | grep "skill-authoring-guide"` → no new warnings.
- [ ] **Step 8:** Commit: `git commit -m "docs: add rationale transformation, L2/L3 judgment row, and lifecycle section to skill-authoring-guide"`

---

### Task 5: Final validation

- [ ] **Step 1:** `python scripts/lint.py --root . --no-urls` → zero failures, zero new warnings vs. pre-change baseline.
- [ ] **Step 2:** Verify all nine changes are present:
  - `grep -c "L1 routing signal" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "tested_with" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "Trigger Evaluation" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "L2 contains instructions" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "Session limit" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "assets/" skills/lint/references/skill-authoring-guide.md` → at least 1
  - `grep -c "Cross-Platform Portability" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "Transformation pattern" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "L2/L3 placement" skills/lint/references/skill-authoring-guide.md` → 1
  - `grep -c "Skill Lifecycle" skills/lint/references/skill-authoring-guide.md` → 1
- [ ] **Step 3:** Confirm section order is preserved: `grep -n "^## " skills/lint/references/skill-authoring-guide.md` → sections appear in order: Loading Model, Required Frontmatter, SKILL.md Body, Reference Files, Cross-Platform Portability, [Examples / Canonical Example], Evaluation Criteria, Skill Lifecycle and Staleness.
- [ ] **Step 4:** Commit: `git commit -m "chore: validate skill-authoring-guide improvements complete"`

---

## Validation

- [ ] `python scripts/lint.py --root . --no-urls` — zero failures, no new warnings
- [ ] `grep "L1 routing signal" skills/lint/references/skill-authoring-guide.md` — present (Change 9)
- [ ] `grep "tested_with" skills/lint/references/skill-authoring-guide.md` — present (Change 3)
- [ ] `grep "Trigger Evaluation" skills/lint/references/skill-authoring-guide.md` — present (Change 5)
- [ ] `grep "L2 contains instructions" skills/lint/references/skill-authoring-guide.md` — present (Change 1a)
- [ ] `grep "Session limit" skills/lint/references/skill-authoring-guide.md` — present (Change 8)
- [ ] `grep "assets/" skills/lint/references/skill-authoring-guide.md` — present (Change 2)
- [ ] `grep "Cross-Platform Portability" skills/lint/references/skill-authoring-guide.md` — present (Change 6)
- [ ] `grep "Transformation pattern" skills/lint/references/skill-authoring-guide.md` — present (Change 4)
- [ ] `grep "L2/L3 placement" skills/lint/references/skill-authoring-guide.md` — present (Change 1b)
- [ ] `grep "Skill Lifecycle" skills/lint/references/skill-authoring-guide.md` — present (Change 7)
- [ ] `scripts/lint.py` not modified: `git diff main -- scripts/lint.py` — no output
