# Report-Issue Skill Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve `/wos:report-issue` with LLM invocability, quality templates, framing guidance, and an advisory quality checklist shown in the preview.

**Architecture:** Three markdown skill files are modified. No Python code, no scripted validation. The quality checklist is agent-applied — the workflow instructions tell the agent what to check and how to display results.

**Tech Stack:** Markdown skill definitions (SKILL.md + references/)

---

### Task 1: Enable LLM invocation in SKILL.md

**Files:**
- Modify: `skills/report-issue/SKILL.md:1-11`

**Step 1: Update the YAML frontmatter**

Replace lines 1-11 of `skills/report-issue/SKILL.md` with:

```yaml
---
name: report-issue
description: >
  Use when the user wants to "report a bug", "submit feedback",
  "request a feature", "file an issue", or when you discover
  a problem, limitation, or missing capability in WOS during
  normal work. Proactively suggest filing when you encounter
  WOS issues the maintainer should know about.
argument-hint: "[describe the issue or feedback]"
---
```

Changes:
- Removed `disable-model-invocation: true` (line 9)
- Rewrote `description` to cover proactive detection triggers
- Kept `argument-hint` unchanged

**Step 2: Verify the file**

Read `skills/report-issue/SKILL.md` and confirm:
- No `disable-model-invocation` field present
- Description includes "when you discover a problem" and "Proactively suggest"
- Rest of file (lines 12-35) unchanged

**Step 3: Commit**

```bash
git add skills/report-issue/SKILL.md
git commit -m "feat(report-issue): enable LLM invocation and proactive triggers (#14)"
```

---

### Task 2: Update bug report template with MRE section

**Files:**
- Modify: `skills/report-issue/references/issue-templates.md:6-36`

**Step 1: Replace the bug report template**

Replace lines 6-36 (the `## Bug Report` section including its fenced code block) with:

```markdown
## Bug Report

```markdown
## Description

[What happened — clear, concise description of the bug]

## Minimum Reproducible Example

[The smallest possible setup that triggers the bug. Include:
- A minimal document fixture (inline or as a file description)
- The exact command or skill invocation
- The exact error output

If the bug requires multiple files, describe the minimal directory
structure needed to reproduce it.]

## Expected Behavior

[What should have happened]

## Actual Behavior

[What actually happened, including full error messages]

## Environment

- **wos version:** [version from plugin.json]
- **Python:** [python3 --version output]
- **Platform:** [uname output]
```
```

Changes:
- Replaced "Steps to Reproduce" (numbered list) with "Minimum Reproducible Example" (structured guidance for minimal fixture + command + error)
- Removed "Additional Context" section (subsumed by MRE)
- Kept Description, Expected/Actual Behavior, Environment sections

**Step 2: Verify the bug report template**

Read the file and confirm the bug report section contains exactly these headings inside the code fence: Description, Minimum Reproducible Example, Expected Behavior, Actual Behavior, Environment.

---

### Task 3: Update feature request template with quality sections

**Files:**
- Modify: `skills/report-issue/references/issue-templates.md:38-60`

**Step 1: Replace the feature request template**

Replace lines 38-60 (the `## Feature Request` section including its fenced code block) with:

```markdown
## Feature Request

```markdown
## Problem

[Describe the problem generically — any WOS user should recognize it.
Avoid references to specific vaults, file counts, or personal workflows.]

## Why This Matters

[1-3 bullet points on impact: who is affected, what breaks or degrades,
why the current state is insufficient. Frame from the tool's perspective.]

## Proposed Solution

[What the feature does and how it works. Include before/after examples
where behavior changes. Include design decisions for non-obvious choices.]

### Scope

[What's included in this proposal.]

### Non-Goals

[What's explicitly excluded to prevent scope creep.]

## Evaluation

### Test Fixtures

[Minimal example files or scenarios that demonstrate the expected behavior.
Each fixture should test one specific aspect.]

| Fixture | Scenario | Expected result |
|---|---|---|
| [file/scenario] | [what it tests] | [pass/fail criteria] |

### Pass Criteria

[Measurable outcomes. How do we know this works?]

| Test | Expected result |
|---|---|
| [specific test] | [specific expected outcome] |

## Alternatives Considered

[Other approaches and why they're less suitable.]

## Environment

- **wos version:** [version from plugin.json]
```
```

Changes:
- Replaced "Use Case" with "Problem" (generic framing guidance in placeholder)
- Added "Why This Matters" section
- Expanded "Proposed Solution" with before/after and design decision guidance
- Added "Scope" and "Non-Goals" as subsections
- Added "Evaluation" with test fixtures table and pass criteria table
- Kept "Alternatives Considered" and "Environment"
- Removed "Additional Context" (subsumed by new sections)

**Step 2: Verify the feature request template**

Read the file and confirm the feature request section contains these headings inside the code fence: Problem, Why This Matters, Proposed Solution, Scope (h3), Non-Goals (h3), Evaluation, Test Fixtures (h3), Pass Criteria (h3), Alternatives Considered, Environment.

**Step 3: Verify General Feedback template is unchanged**

Confirm lines 62-81 (General Feedback section) are identical to the original.

**Step 4: Commit templates**

```bash
git add skills/report-issue/references/issue-templates.md
git commit -m "feat(report-issue): update bug/feature templates with MRE and evaluation sections (#14)"
```

---

### Task 4: Add framing guidance to Phase 4

**Files:**
- Modify: `skills/report-issue/references/report-issue-submit.md:59-66`

**Step 1: Expand Phase 4 with framing guidance**

Replace lines 59-66 (Phase 4 section) with:

```markdown
## Phase 4: Draft the Issue

Use the appropriate template from `references/issue-templates.md`.

Fill in:
- **Title**: Concise summary (under 70 characters)
- **Body**: From the template, with gathered context
- **Labels**: From classification above

### Framing Rule

Write issues from the WOS tool author's perspective, not the consumer's.
The reader is the WOS maintainer who needs to understand, reproduce, and
fix the issue.

- Replace vault-specific details with generic examples
- Use "a WOS user" or "a project with N context files" instead of "I"
  or "my vault"
- Describe solutions in terms of WOS's internal architecture (scripts,
  validators, skills)
- If the user provides consumer-specific context, extract the generic
  pattern

**Consumer-specific details to catch and generalize:**
- References to specific vault files or directory structures
- Exact file counts or token numbers from a specific deployment
- "During my recent X" narratives tied to a particular workflow
- Vault-specific template names, area names, or project structures
```

Changes:
- Original Phase 4 content preserved (lines 59-66)
- Added "Framing Rule" subsection with rewriting guidance
- Added concrete list of consumer-specific details to catch

**Step 2: Verify Phase 4**

Read the file and confirm Phase 4 now contains both the original fill-in instructions and the new "Framing Rule" subsection.

---

### Task 5: Add quality checklist to Phase 5 preview

**Files:**
- Modify: `skills/report-issue/references/report-issue-submit.md:68-85`

**Step 1: Expand Phase 5 with quality checklist**

Replace lines 68-85 (Phase 5 section) with:

```markdown
## Phase 5: Preview and Quality Check

Before showing the preview, evaluate the draft against the quality
checklist below. Show results alongside the draft.

### Quality Checklist

Apply the checks relevant to the issue type:

| Check | Applies to | Pass criteria |
|---|---|---|
| Generic framing | All types | No vault-specific paths, file counts, or "my vault" language |
| Self-contained | All types | Understandable without reading prior conversations or external context |
| Has evaluation criteria | Feature requests | Test fixtures table and pass criteria table are present and filled in |
| Has MRE | Bug reports | Minimum reproducible example section is present with fixture + command + error |
| Has before/after examples | Features changing existing behavior | Current vs proposed output shown |
| Has scope/non-goals | Feature requests | Scope and Non-Goals subsections are present and filled in |

### Preview Format

Show the user the complete issue draft with quality check results:

```
──────────────────────────────────────
Title: [issue title]
Labels: [labels]
Repo: bcbeidel/wos
──────────────────────────────────────
[full issue body]
──────────────────────────────────────

Quality Checks:
  ✓ Generic framing
  ✓ Self-contained
  ⚠ [any checks that didn't fully pass — explain briefly]
```

All checks are **advisory**. The user can approve and submit even if
some checks show warnings.

Ask: "Does this look right? I can edit any part before submitting."

Wait for explicit approval. If the user requests changes, apply them
and preview again.
```

Changes:
- Renamed from "Preview" to "Preview and Quality Check"
- Added quality checklist table with per-type applicability
- Updated preview format to include quality check results
- Kept the approval flow (ask, wait, re-preview if changes requested)

**Step 2: Verify Phase 5**

Read the file and confirm:
- Phase 5 heading is "Preview and Quality Check"
- Quality checklist table has 6 rows
- Preview format block includes "Quality Checks:" section
- Advisory note is present
- Approval flow is preserved

**Step 3: Verify Phase 6 is unchanged**

Confirm Phase 6 (Submit) is identical to the original.

**Step 4: Commit workflow changes**

```bash
git add skills/report-issue/references/report-issue-submit.md
git commit -m "feat(report-issue): add framing guidance and quality checklist to workflow (#14)"
```

---

### Task 6: End-to-end verification

**Step 1: Read all three files and verify consistency**

Read each file and confirm:
- `SKILL.md`: No `disable-model-invocation`, description includes proactive triggers
- `issue-templates.md`: Bug has MRE, Feature has 7 sections, Feedback unchanged
- `report-issue-submit.md`: Phase 4 has framing rule, Phase 5 has quality checklist, Phases 1-3 and 6 unchanged

**Step 2: Test the skill with a real issue**

Invoke `/wos:report-issue` with a test issue provided by the user. Verify:
- The agent follows the updated Phase 4 framing guidance
- The preview includes quality check results
- The template sections match the updated templates

---
