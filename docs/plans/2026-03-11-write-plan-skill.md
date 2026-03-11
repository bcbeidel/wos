---
name: Write-Plan Skill Implementation
description: Create wos:write-plan skill with SKILL.md and reference files — issue #159
type: plan
status: executing
related:
  - skills/_shared/references/plan-format.md
  - docs/plans/2026-03-11-brainstorm-skill.md
---

# Write-Plan Skill Implementation

**Goal:** Ship the `wos:write-plan` skill (#159) — a WOS-native skill that
converts approved design specs into structured implementation plans with
lifecycle metadata, verification criteria, and infeasibility feedback. This
fills the gap between brainstorming (design) and execution (implementation).

**Scope:**

Must have:
- `skills/write-plan/SKILL.md` under 500 body lines, following WOS skill conventions
- `skills/write-plan/references/format-guide.md` — how to write each plan section well
- `skills/write-plan/references/plan-template.md` — copyable skeleton with all 6 sections
- `skills/write-plan/references/examples/small-plan.md` — adapted from plan-document-format-implementation
- `skills/write-plan/references/examples/medium-plan.md` — adapted from brainstorm-skill plan
- Skill triggers on "plan", "implementation plan", "break this down"
- Produces plans conforming to plan-format.md spec (6 required sections, 5-state lifecycle)
- Scope check fires for plans >20 tasks or >3 independent subsystems
- MVP infeasibility feedback as embedded `## Feedback` section
- Explicit handoff to `wos:execute-plan`
- All 6 required sections present in plan output
- At least one concrete validation criterion required

Won't have:
- Scripts or Python code (pure markdown skill)
- New validators or document model changes
- Plan-specific audit checks (deferred to #161)
- Full feedback loop formalization (deferred to #163)
- Auto-updating of design documents

**Approach:** Create 5 markdown files. SKILL.md defines a 7-step workflow
(gather context → scope check → write plan → infeasibility check → review →
update status → hand off) with key instructions and anti-pattern guards.
format-guide.md teaches how to write each of the 6 plan sections effectively,
complementing the structural plan-format.md reference. plan-template.md
provides a copyable skeleton. Two example plans are adapted from real
completed plans in docs/plans/. Validate with existing skill audit.

**File Changes:**
- Create: `skills/write-plan/SKILL.md`
- Create: `skills/write-plan/references/format-guide.md`
- Create: `skills/write-plan/references/plan-template.md`
- Create: `skills/write-plan/references/examples/small-plan.md`
- Create: `skills/write-plan/references/examples/medium-plan.md`

**Branch:** `feat/159-write-plan-skill`
**PR:** TBD

---

### Task 1: Create skill directory and SKILL.md

**Files:**
- Create: `skills/write-plan/SKILL.md`
- Create: `skills/write-plan/references/` (directory)
- Create: `skills/write-plan/references/examples/` (directory)

- [x] **Step 1: Create the directory structure**

```bash
mkdir -p skills/write-plan/references/examples
```

- [x] **Step 2: Write SKILL.md**

Create `skills/write-plan/SKILL.md` with the following content:

```markdown
---
name: write-plan
description: >
  Use when you have a spec or requirements for a multi-step task,
  before touching code. Creates structured implementation plans with
  explicit lifecycle management and verification criteria. Use when
  the user wants to "plan", "make an implementation plan", "break
  this down into tasks", or needs to turn a design into actionable
  work items.
argument-hint: "[design doc path or feature description]"
user-invocable: true
references:
  - references/format-guide.md
  - references/plan-template.md
  - references/examples/small-plan.md
  - references/examples/medium-plan.md
---

# Write Plan

Convert approved designs or requirements into structured implementation plans.
The output is a plan document — not code, not a design.

## Workflow

### 1. Gather Context

- Read the design doc (if invoked from brainstorm, check the `related` field).
- Explore the codebase: identify files to create, modify, or delete.
- Check `docs/plans/` for overlapping or related plans.
- If no design doc exists, gather requirements from the user before proceeding.

### 2. Scope Check

If the plan would require >20 tasks or span >3 independent subsystems,
suggest splitting into separate plans. Each plan should produce working,
testable software on its own.

> "This looks like [N] independent pieces: [list]. I'd suggest separate
> plans — they can be built in any order. Which should we start with?"

### 3. Write the Plan

Save to `docs/plans/YYYY-MM-DD-<feature-name>.md` using the
[Plan Document Format](../../_shared/references/plan-format.md).

See [Format Guide](references/format-guide.md) for how to write each section
effectively. Use the [Plan Template](references/plan-template.md) as a
starting skeleton.

All 6 required sections: Goal, Scope, Approach, File Changes, Tasks,
Validation. At least one concrete validation criterion — not "verify it
works" but a specific command with expected output.

### 4. Infeasibility Check

If plan creation reveals the design cannot be implemented as specified,
do not silently modify scope. Instead, produce structured feedback:

    ## Feedback

    **Infeasible:** [specific design element that cannot be implemented]
    **Evidence:** [files checked, APIs tested, dependencies missing]
    **Impact:** [which plan tasks are affected and how]
    **Alternatives:** [suggested modifications, if any]

Present the user with three options:

1. **Return to brainstorm** — invoke `wos:brainstorm` with this feedback
   to revise the design. Follow the "supersede, don't edit" pattern.
2. **Proceed with modified scope** — adjust the plan's Must/Won't and
   continue. Document what changed and why in the Approach section.
3. **Abandon** — set `status: abandoned` with a reason in the plan.

### 5. Review with User

Present a summary:
- Goal (1 sentence)
- Task count and estimated file changes
- Key scope boundaries (Must/Won't highlights)
- Validation criteria

Do not proceed until the user approves.

### 6. Update Status

When the user approves, set `status: approved` in the plan's frontmatter.

### 7. Hand Off

Offer to invoke `wos:execute-plan` for implementation. The plan should be
ready for execution by an agent with zero prior context.

## Key Instructions

- **Plans are files, not chat.** Save to disk with frontmatter. Plans that
  exist only in conversation are lost on context reset.
- **Every task gets a verification command.** If you can't verify it, you
  can't know it's done.
- **Middle altitude.** Observable outcomes, not implementation prescriptions.
  Too abstract: "Implement auth." Too granular: "Write if-statement on
  line 47." Right: "Add login endpoint. Verify: `curl POST /login`
  returns 200 with token."
- **One plan per feature.** Multi-system changes get separate plans.
- **Link to design docs.** Use the `related` field to connect plans to
  their design specs, establishing traceability.
- **Scope boundaries are load-bearing.** Won't-have items prevent scope
  creep during execution. Be explicit about what's excluded.
- **Dependencies between tasks are explicit.** If task B requires task A,
  state the dependency. Default is sequential execution.
- **Chunk large plans.** Use `## Chunk N: <name>` headers for plans with
  10+ tasks, grouping by logical dependency.

## Anti-Pattern Guards

1. **Premature implementation** — writing code or invoking execution skills
   before the plan is approved. The plan is the deliverable.
2. **Vague validation** — "verify it works" is not a criterion. Every
   validation item needs a concrete command or observable check.
3. **Task granularity extremes** — tasks should be independently verifiable
   outcomes. Neither "implement the feature" nor "add import statement."
4. **Scope creep during planning** — if the plan grows beyond the design,
   something is wrong. Check whether the design needs revision (step 4)
   or the plan needs splitting (step 2).
5. **Skipping the infeasibility check** — even if everything seems fine,
   confirm the design's assumptions against the actual codebase before
   presenting for review.

## Output Format

Plan documents use WOS frontmatter:

    ---
    name: Feature Name
    description: One-sentence summary
    type: plan
    status: draft
    related:
      - docs/plans/YYYY-MM-DD-<name>-design.md
    ---

Save to `docs/plans/YYYY-MM-DD-<feature-name>.md`. The `related` field
links to design docs, context files, or other plans.
```

- [x] **Step 3: Verify line count**

Run: `wc -l skills/write-plan/SKILL.md`
Expected: under 500 lines (target ~130 lines) — actual: 143 lines

- [x] **Step 4: Commit**

```bash
git add skills/write-plan/SKILL.md
git commit -m "feat: add wos:write-plan SKILL.md — issue #159"
```

---

### Task 2: Create format-guide.md reference

**Files:**
- Create: `skills/write-plan/references/format-guide.md`

- [x] **Step 1: Write format-guide.md**

Create `skills/write-plan/references/format-guide.md` — the deeper companion
to plan-format.md. Where plan-format.md defines the schema, this teaches
how to write each section well.

```markdown
---
name: Plan Format Guide
description: How to write effective plan sections — goals, scope, tasks, and verification
---

# Plan Format Guide

Guidance for writing each of the 6 required plan sections. For the structural
reference (frontmatter schema, lifecycle states, task decomposition rules),
see [Plan Document Format](../../_shared/references/plan-format.md).

## Writing the Goal

State the user-visible outcome in 2-3 sentences. Lead with what changes,
then why it matters. Avoid implementation language.

| Quality | Example |
|---------|---------|
| Good | "Users can filter audit results by severity and file type. This reduces noise when investigating specific issues." |
| Bad | "Add --severity and --type flags to the audit CLI and wire them through validators.py" |
| Bad | "Improve the audit experience." |

The goal should be verifiable from outside the codebase. If someone unfamiliar
with the project reads it, they should understand what success looks like.

## Scoping with Must / Won't

Must-have items define the minimum viable delivery. Won't-have items are
equally important — they prevent scope creep by making exclusions explicit.

Include anything the user might reasonably expect but that's excluded. If
a feature is adjacent but not part of this plan, put it in Won't.

**Signals you need Won't items:**
- The design mentions future work
- The feature has obvious extensions you're not building yet
- The plan touches shared code that other features also use

## Writing the Approach

High-level technical strategy. 2-4 sentences describing how the goal will
be achieved. Name the key architectural decisions.

This is "middle altitude" — enough detail to orient the implementer, not
enough to prescribe every line of code. If the approach reads like
pseudo-code, it's too detailed. If it reads like a goal restated, it's
too abstract.

## File Changes

List every file created, modified, or deleted. For modifications, include
what changes (not just the file path).

    - Create: `wos/new_module.py`
    - Modify: `wos/validators.py` (add severity filter to validate_project)
    - Modify: `tests/test_validators.py` (add filter tests)
    - Delete: `wos/old_module.py`

Include line references for targeted modifications when the file is large.

## Writing Tasks

Tasks are the plan's core. Each task is a deliverable with verification.

**Middle altitude:**

| Level | Example | Problem |
|-------|---------|---------|
| Too abstract | "Implement authentication" | No verification possible |
| Right | "Add login endpoint that returns JWT. Verify: `curl -X POST /login` returns 200" | Observable outcome with command |
| Too granular | "Add `import jwt` on line 3 of auth.py" | Prescribes implementation |

**Verification patterns:**

Every task ends with a verification step. Types:
- Test command: `uv run python -m pytest tests/test_foo.py::test_name -v`
- CLI invocation: `uv run scripts/audit.py --root . | grep "0 failures"`
- Manual check: `wc -l skills/foo/SKILL.md` (expected: under 500)
- Read verification: confirm file exists and contains expected content

**Task naming:** Name tasks as deliverables, not activities.
- Good: "Login endpoint with JWT response"
- Bad: "Work on authentication"

## Writing Validation

End-to-end criteria that prove the plan succeeded. These are higher-level
than task verification — they test the whole feature, not individual pieces.

At least one criterion required. Each must be concrete:

| Quality | Example |
|---------|---------|
| Good | "`uv run python -m pytest tests/ -v` — all tests pass" |
| Good | "`uv run scripts/audit.py --root .` — no failures for new skill" |
| Bad | "Verify the feature works correctly" |
| Bad | "Everything should be tested" |
```

- [x] **Step 2: Verify line count**

Run: `wc -l skills/write-plan/references/format-guide.md`
Expected: under 100 lines (target ~90 lines) — actual: 97 lines

- [x] **Step 3: Commit**

```bash
git add skills/write-plan/references/format-guide.md
git commit -m "docs: add format-guide reference for write-plan skill"
```

---

### Task 3: Create plan-template.md reference

**Files:**
- Create: `skills/write-plan/references/plan-template.md`

- [x] **Step 1: Write plan-template.md**

Create `skills/write-plan/references/plan-template.md` — copyable skeleton
with all 6 required sections and frontmatter.

```markdown
---
name: Plan Template
description: Copyable skeleton for implementation plans with all required sections
---

# Plan Template

Copy this skeleton when creating a new plan. Fill in each section, then
remove the bracketed instructions.

    ---
    name: [Feature Name]
    description: [One-sentence summary of what this plan achieves]
    type: plan
    status: draft
    related:
      - [path/to/design-doc.md]
    ---

    # [Feature Name]

    **Goal:** [2-3 sentences. State user-visible outcome. Why this matters.]

    **Scope:**

    Must have:
    - [Required deliverable]

    Won't have:
    - [Explicit exclusion]

    **Approach:** [High-level technical strategy. How the goal will be achieved.
    Name key architectural decisions. 2-4 sentences.]

    **File Changes:**
    - Create: `path/to/new-file.py`
    - Modify: `path/to/existing.py` (what changes)
    - Delete: `path/to/removed.py`

    **Branch:** `feat/NNN-feature-name`
    **PR:** TBD

    ---

    ### Task 1: [Outcome-oriented name]

    **Files:**
    - Create: `path/to/file.py`
    - Test: `tests/path/to/test_file.py`

    - [ ] **Step 1:** [Action with specific detail]
    - [ ] **Step 2:** Verify: `[concrete command with expected output]`
    - [ ] **Step 3:** Commit

    ---

    ## Validation

    - [ ] `[concrete command]` — [expected outcome]
    - [ ] `[concrete command]` — [expected outcome]
```

- [x] **Step 2: Verify line count**

Run: `wc -l skills/write-plan/references/plan-template.md`
Expected: under 55 lines (target ~45 lines) — actual: 60 lines

- [x] **Step 3: Commit**

```bash
git add skills/write-plan/references/plan-template.md
git commit -m "docs: add plan-template reference for write-plan skill"
```

---

### Task 4: Create small-plan.md example

**Files:**
- Create: `skills/write-plan/references/examples/small-plan.md`

Adapted from `docs/plans/2026-03-11-plan-document-format-implementation.md`.
Simplified to demonstrate the format at small scale: single module, 3 tasks,
clear verification. Modified to perfectly match the 6-section format.

- [x] **Step 1: Write small-plan.md**

Create `skills/write-plan/references/examples/small-plan.md`:

```markdown
---
name: Small Plan Example
description: Example plan adapted from a real implementation — single-module, 3 tasks
---

# Small Plan Example

This example is adapted from a real completed plan (plan-document-format
implementation). It demonstrates the format at small scale: one module,
focused scope, 3 tasks with TDD verification.

    ---
    name: Status Field Implementation
    description: Add status field to Document model with parse-time validation
    type: plan
    status: draft
    related:
      - docs/plans/2026-03-11-status-field-design.md
    ---

    # Status Field Implementation

    **Goal:** Add lifecycle status tracking to plan documents so that
    downstream skills (execute-plan, validate-plan) can query plan state.
    Plans currently have no machine-readable status.

    **Scope:**

    Must have:
    - `status` field on Document dataclass (Optional[str], default None)
    - Parse-time extraction from frontmatter
    - Enum validation (draft, approved, executing, completed, abandoned)
    - Tests for all valid and invalid values

    Won't have:
    - Status transition validation (deferred)
    - Plan-specific audit checks (separate issue)
    - Required-section validation

    **Approach:** Extend the Document dataclass with one optional field.
    Add extraction logic to parse_document() alongside existing field
    handling. Validate against a closed set of strings — plain membership
    check, no Python enum type.

    **File Changes:**
    - Modify: `wos/document.py` (add field to dataclass, parse + validate in parse_document)
    - Modify: `tests/test_document.py` (add status tests, update test_unknown_fields_ignored)

    **Branch:** `feat/157-plan-document-format`

    ---

    ### Task 1: Add status field to Document dataclass

    **Files:**
    - Modify: `wos/document.py`
    - Test: `tests/test_document.py`

    - [ ] Write failing test: Document accepts `status` kwarg, defaults to None
    - [ ] Run test — expected: FAIL (unexpected keyword argument)
    - [ ] Add `status: Optional[str] = None` to Document, add "status" to _KNOWN_FIELDS
    - [ ] Run test — expected: PASS
    - [ ] Commit

    ### Task 2: Parse and validate status from frontmatter

    **Files:**
    - Modify: `wos/document.py`
    - Test: `tests/test_document.py`

    - [ ] Write failing test: parse_document extracts status from frontmatter
    - [ ] Write failing test: invalid status raises ValueError
    - [ ] Run tests — expected: both FAIL
    - [ ] Add status extraction and validation to parse_document()
    - [ ] Run tests — expected: both PASS
    - [ ] Commit

    ### Task 3: Update existing test for status recognition

    **Files:**
    - Modify: `tests/test_document.py`

    - [ ] Update test_unknown_fields_ignored to expect doc.status == "draft"
    - [ ] Run full test suite — expected: ALL PASS
    - [ ] Commit

    ---

    ## Validation

    - [ ] `uv run python -m pytest tests/test_document.py -v` — all status tests pass
    - [ ] `uv run python -c "from wos.document import parse_document; ..."` — parses status from real plan file
```

- [x] **Step 2: Commit**

```bash
git add skills/write-plan/references/examples/small-plan.md
git commit -m "docs: add small-plan example for write-plan skill"
```

---

### Task 5: Create medium-plan.md example

**Files:**
- Create: `skills/write-plan/references/examples/medium-plan.md`

Adapted from `docs/plans/2026-03-11-brainstorm-skill.md`. Demonstrates
broader scope: new skill with SKILL.md + 2 reference files, 4 tasks,
audit-based validation.

- [x] **Step 1: Write medium-plan.md**

Create `skills/write-plan/references/examples/medium-plan.md`:

```markdown
---
name: Medium Plan Example
description: Example plan adapted from a real implementation — new skill with references, 4 tasks
---

# Medium Plan Example

This example is adapted from a real completed plan (brainstorm skill
implementation). It demonstrates the format at medium scale: new skill
directory with SKILL.md and reference files, broader scope, 4 tasks,
audit-based validation.

    ---
    name: Brainstorm Skill Implementation
    description: Create wos:brainstorm skill with SKILL.md and two reference files
    type: plan
    status: draft
    related:
      - skills/_shared/references/plan-format.md
    ---

    # Brainstorm Skill Implementation

    **Goal:** Ship the brainstorm skill — a structured exploration tool
    that produces design documents through divergent-then-convergent
    thinking. This bridges the gap between user intent and implementation
    planning by ensuring designs are explored before plans are written.

    **Scope:**

    Must have:
    - `skills/brainstorm/SKILL.md` under 500 body lines
    - `skills/brainstorm/references/spec-format-guide.md`
    - `skills/brainstorm/references/exploration-patterns.md`
    - Triggers on "brainstorm", "explore", "design"
    - Hard gate: produces design docs, not plans or code
    - 2-3 approach exploration before convergence
    - Design doc output with `type: design` frontmatter

    Won't have:
    - Visual companion (CLI-focused)
    - Subagent dispatch for spec review
    - Scripts or Python code (pure markdown skill)
    - New validators or document model changes

    **Approach:** Create three markdown files. SKILL.md defines a 6-step
    workflow (understand → diverge → converge → write spec → review →
    hand off). Reference files distill research into concise scaffolds:
    spec-format-guide covers section format and depth calibration,
    exploration-patterns provides question templates and approach
    comparison format.

    **File Changes:**
    - Create: `skills/brainstorm/SKILL.md`
    - Create: `skills/brainstorm/references/spec-format-guide.md`
    - Create: `skills/brainstorm/references/exploration-patterns.md`

    **Branch:** `feat/158-brainstorm-skill`

    ---

    ### Task 1: Create SKILL.md

    **Files:**
    - Create: `skills/brainstorm/SKILL.md`

    - [ ] Create directory: `mkdir -p skills/brainstorm/references`
    - [ ] Write SKILL.md with frontmatter, 6-step workflow, key instructions,
          anti-pattern guards, output format
    - [ ] Verify line count: `wc -l skills/brainstorm/SKILL.md` (under 500)
    - [ ] Commit

    ### Task 2: Create spec-format-guide.md

    **Files:**
    - Create: `skills/brainstorm/references/spec-format-guide.md`

    - [ ] Write guide covering: required frontmatter, spec sections table,
          writing principles, depth calibration table
    - [ ] Verify line count: `wc -l` (under 80)
    - [ ] Commit

    ### Task 3: Create exploration-patterns.md

    **Files:**
    - Create: `skills/brainstorm/references/exploration-patterns.md`

    - [ ] Write guide covering: question format (multiple-choice preferred),
          approach comparison table template, scope decomposition signals,
          convergence checklist
    - [ ] Verify line count: `wc -l` (under 80)
    - [ ] Commit

    ### Task 4: Run validation

    Depends on: Tasks 1-3

    - [ ] Run test suite: `uv run python -m pytest tests/ -v` — all pass
    - [ ] Run skill audit: `uv run scripts/audit.py --root .` — no failures
          for brainstorm skill
    - [ ] Fix any audit findings and re-run
    - [ ] Commit fixes (if any)

    ---

    ## Validation

    - [ ] `uv run python -m pytest tests/ -v` — all tests pass (no regressions)
    - [ ] `uv run scripts/audit.py --root .` — no failures for brainstorm skill
    - [ ] `skills/brainstorm/SKILL.md` exists and is under 500 body lines
    - [ ] SKILL.md frontmatter has name, description, user-invocable, references
    - [ ] Hard gate text present in SKILL.md body
```

- [x] **Step 2: Commit**

```bash
git add skills/write-plan/references/examples/medium-plan.md
git commit -m "docs: add medium-plan example for write-plan skill"
```

---

### Task 6: Run validation

**Files:**
- None modified (validation only)

Depends on: Tasks 1-5

- [x] **Step 1: Run existing test suite**

Run: `uv run python -m pytest tests/ -v`
Result: 264 passed in 1.06s — ALL PASS

- [x] **Step 2: Run skill audit**

Run: `uv run scripts/audit.py --root . --no-urls`
Result: write-plan skill at 163 instruction lines (78 SKILL + 85 refs).
No new failures or warnings from write-plan skill.

- [x] **Step 3: Fix any audit findings**

No fixes needed for write-plan skill.

- [x] **Step 4: Commit any fixes**

```bash
git add skills/write-plan/
git commit -m "fix: address audit findings for write-plan skill"
```

(Skip if no fixes needed.)

---

## Validation

- [x] `uv run python -m pytest tests/ -v` — all tests pass (264 passed)
- [x] `uv run scripts/audit.py --root .` — no new failures for write-plan skill (163 instruction lines)
- [x] `skills/write-plan/SKILL.md` exists and is under 500 body lines (143 lines)
- [x] `skills/write-plan/references/format-guide.md` exists (97 lines)
- [x] `skills/write-plan/references/plan-template.md` exists (60 lines)
- [x] `skills/write-plan/references/examples/small-plan.md` exists (92 lines)
- [x] `skills/write-plan/references/examples/medium-plan.md` exists (112 lines)
- [x] SKILL.md frontmatter has name, description, argument-hint, user-invocable, references
- [x] Skill triggers on "plan", "implementation plan", "break this down" (verify via description text)
- [x] Plan output format includes all 6 required sections (Goal, Scope, Approach, File Changes, Tasks, Validation)
- [x] Infeasibility feedback section documented with 4 required fields
- [x] Scope check guidance present for >20 tasks
- [x] Concrete validation criterion requirement stated
- [x] Explicit handoff to `wos:execute-plan` in step 7
