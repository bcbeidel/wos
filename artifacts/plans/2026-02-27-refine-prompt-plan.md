---
name: Refine-Prompt Skill Implementation Plan
description: Step-by-step implementation for /wos:refine-prompt skill with assessment rubric and technique registry
type: plan
related:
  - artifacts/plans/2026-02-27-refine-prompt-design.md
---

# Refine-Prompt Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `/wos:refine-prompt` skill that assesses and refines prompts using evidence-backed techniques in a three-stage pipeline.

**Architecture:** Skill-only (no Python scripts). SKILL.md defines the 3-stage pipeline (Assess → Refine → Present). Two reference files provide the assessment rubric and technique registry. Follows existing skill patterns — SKILL.md as gateway, references/ for depth.

**Tech Stack:** Markdown only. No Python, no dependencies.

**Issue:** [#71](https://github.com/bcbeidel/wos/issues/71)
**Branch:** `feat/71-refine-prompt`
**PR:** (pending)

### Progress

- [x] Task 1: Create SKILL.md
- [x] Task 2: Create assessment rubric reference
- [x] Task 3: Create technique registry reference
- [x] Task 4: Verify skill discovery and run tests (171/171 pass)
- [x] Task 5: Update plan doc and close out

---

### Task 1: Create SKILL.md

**Files:**
- Create: `skills/refine-prompt/SKILL.md`

**Context:** Look at `skills/distill/SKILL.md` and `skills/research/SKILL.md` for the pattern. SKILL.md has YAML frontmatter, then the skill content. It's the gateway — it defines the pipeline and key rules, referencing other files for detail.

**Step 1: Create the skill directory**

```bash
mkdir -p skills/refine-prompt/references
```

**Step 2: Write SKILL.md**

Create `skills/refine-prompt/SKILL.md` with this exact content:

```markdown
---
name: refine-prompt
description: >
  This skill should be used when the user wants to "improve a prompt",
  "refine this prompt", "make this prompt better", "assess prompt quality",
  "optimize this prompt", or review any prompt text or SKILL.md instruction
  block for clarity, structure, and completeness.
argument-hint: "[prompt text or file path]"
user-invocable: true
references:
  - references/technique-registry.md
  - references/assessment-rubric.md
---

# Refine Prompt

Assess and refine prompts using evidence-backed techniques. Runs a three-stage
pipeline: **Assess → Refine → Present**.

## Input

Accept either:
- **Inline text** — prompt pasted directly after the command
- **File path** — path to a file containing the prompt (e.g., a SKILL.md)

If a file path is given, read the file and use its content as the prompt.

## Pipeline

### 1. Assess

Score the prompt on three dimensions using the
[assessment rubric](references/assessment-rubric.md):

| Dimension | What it measures |
|-----------|-----------------|
| Clarity | Unambiguous language, specific intent, no undefined jargon |
| Structure | Logical organization, scannable layout, XML tags where useful |
| Completeness | Output format specified, success criteria defined, edge cases addressed |

Each dimension is scored 1-5.

**Early exit:** If all three dimensions score 4+ and no technique condition
in the registry triggers, report that the prompt is well-formed and stop.
Do not refine prompts that don't need it.

### 2. Refine

Walk the [technique registry](references/technique-registry.md) in priority
order (1 through 7). For each technique:

1. Check the **when-to-apply** condition against the current prompt
2. If the condition is met, apply the technique
3. If not, skip to the next technique

Apply techniques iteratively — each builds on the previous output. Stop when
all dimensions reach 4+ and no remaining technique condition triggers.

**Key constraint:** Be selective. Over-prompting degrades Claude 4.x
performance. Apply only techniques whose conditions are clearly met.

### 3. Present

Show the user:

1. **Assessment scores** — before and after, per dimension
2. **Refined prompt** — the complete improved prompt, ready to copy
3. **Change log** — each modification listed with:
   - What changed (brief description)
   - Why (rationale tied to a dimension)
   - Evidence (research citation from the technique registry)

Format the output as:

```
## Assessment

| Dimension | Before | After |
|-----------|--------|-------|
| Clarity | X/5 | Y/5 |
| Structure | X/5 | Y/5 |
| Completeness | X/5 | Y/5 |

## Refined Prompt

[Complete prompt text here, ready to copy]

## Change Log

| # | Change | Rationale | Evidence |
|---|--------|-----------|----------|
| 1 | [What changed] | [Why, tied to dimension] | [Citation] |
```

## Key Rules

- **Manual invocation only.** This skill runs when the user asks. Never
  trigger it automatically or suggest it unprompted.
- **Selective refinement.** Apply only techniques whose conditions are met.
  More techniques ≠ better prompts.
- **Respect well-formed prompts.** If the prompt scores 4+ across all
  dimensions, say so and stop. Don't add noise.
- **Evidence-backed changes.** Every modification in the change log must cite
  the research backing the technique used.
- **Preserve intent.** Refinement improves expression, not meaning. Never
  change what the prompt asks for.
```

**Step 3: Verify the file is well-formed**

Run: `head -15 skills/refine-prompt/SKILL.md`
Expected: Shows the YAML frontmatter with `name: refine-prompt`

**Step 4: Commit**

```bash
git add skills/refine-prompt/SKILL.md
git commit -m "feat: add refine-prompt SKILL.md — 3-stage pipeline (#71)"
```

---

### Task 2: Create Assessment Rubric Reference

**Files:**
- Create: `skills/refine-prompt/references/assessment-rubric.md`

**Context:** This is a reference file (like `skills/distill/references/distillation-guidelines.md`). It provides the scoring rubric that Stage 1 (Assess) uses. Three dimensions, each scored 1-5, with concrete examples at each level so the LLM has clear anchors.

**Step 1: Write the assessment rubric**

Create `skills/refine-prompt/references/assessment-rubric.md` with this exact content:

```markdown
# Assessment Rubric

Three dimensions, each scored 1-5. Use the examples below as anchors.

## Clarity (Is the intent unambiguous?)

| Score | Description | Example |
|-------|-------------|---------|
| 1 | Vague or ambiguous; multiple interpretations possible | "Make it better" |
| 2 | General direction clear but key terms undefined | "Optimize the performance" |
| 3 | Intent clear but some ambiguity in scope or terms | "Improve the API response time" |
| 4 | Specific and unambiguous; minor clarifications possible | "Reduce P95 API latency for the /users endpoint" |
| 5 | Crystal clear; no reasonable misinterpretation possible | "Reduce P95 latency for GET /users from 800ms to under 200ms by adding Redis caching" |

## Structure (Is it organized and scannable?)

| Score | Description | Example |
|-------|-------------|---------|
| 1 | Wall of text, no organization | Single paragraph mixing instructions, context, and constraints |
| 2 | Some separation but no clear sections | Loosely ordered sentences with line breaks |
| 3 | Logical flow but not scannable | Numbered steps without headers or grouping |
| 4 | Well-organized with clear sections | Headers or XML tags separating context, task, and output format |
| 5 | Optimally structured for the model | XML-tagged sections, clear hierarchy, scannable at every level |

## Completeness (Does it specify what success looks like?)

| Score | Description | Example |
|-------|-------------|---------|
| 1 | No output format, no criteria, no constraints | "Write some tests" |
| 2 | Output format OR criteria mentioned, not both | "Write unit tests" (format implied, no criteria) |
| 3 | Output format and basic criteria present | "Write pytest tests that cover the happy path" |
| 4 | Format, criteria, and constraints specified | "Write pytest tests covering happy path and error cases, assert specific return values" |
| 5 | Format, criteria, constraints, and edge cases | "Write pytest tests: happy path, invalid input, empty input, concurrent access. Each test asserts specific return values. Use tmp_path for file operations." |

## Scoring Guidelines

- Score each dimension independently
- Use the examples as anchors, not exact matches
- A prompt scoring 4+ on all dimensions is well-formed — do not refine
- A score of 3 means "acceptable but improvable" — refine if a technique
  condition is met
- A score of 1-2 means "needs work" — techniques will almost certainly apply
```

**Step 2: Verify the file exists**

Run: `head -5 skills/refine-prompt/references/assessment-rubric.md`
Expected: Shows `# Assessment Rubric`

**Step 3: Commit**

```bash
git add skills/refine-prompt/references/assessment-rubric.md
git commit -m "feat: add assessment rubric reference for refine-prompt (#71)"
```

---

### Task 3: Create Technique Registry Reference

**Files:**
- Create: `skills/refine-prompt/references/technique-registry.md`

**Context:** This is the second reference file. It contains 7 techniques in Pareto priority order. Each technique has: description, when-to-apply, when-to-skip, how-to-apply instructions, and evidence citation. The technique registry is separate from SKILL.md so techniques can be updated as research evolves without touching the pipeline logic.

**Step 1: Write the technique registry**

Create `skills/refine-prompt/references/technique-registry.md` with this exact content:

```markdown
# Technique Registry

7 techniques in Pareto priority order. Walk this list top-to-bottom during
Stage 2 (Refine). For each technique, check the **when-to-apply** condition.
If met, apply. If not, skip.

**Key principle:** Apply only techniques whose conditions are clearly met.
More techniques does not mean a better prompt.

---

## 1. Clarity Rewrite

**Impact:** HIGH
**When to apply:** Clarity score < 5
**When to skip:** Clarity already 5/5

Rewrite for directness and specificity:
- Replace vague verbs ("handle", "process", "manage") with specific actions
- Define ambiguous terms inline
- Remove hedging language ("try to", "maybe", "if possible")
- Use second person ("You are..." / "Your task is...")

**Evidence:** Bsharat et al. "Principled Instructions Are All You Need"
(arXiv:2312.16171) — 26 principles for prompting, +57% accuracy on LLaMA-2,
+67% on GPT-4.

---

## 2. XML Structuring

**Impact:** HIGH
**When to apply:** Multi-section prompt OR prompt has 3+ distinct components
(context, task, format, constraints, examples)
**When to skip:** Single-purpose prompt under ~50 words

Wrap distinct sections in XML tags:
- `<context>` for background information
- `<task>` for the main instruction
- `<output_format>` for expected output structure
- `<constraints>` for rules and limitations
- `<examples>` for few-shot examples

Use descriptive tag names. Nest when hierarchy is natural.

**Evidence:** Anthropic Tier 1 documentation — XML tags provide up to 40%
quality improvement on complex prompts. Claude uses tags as parsing boundaries.

---

## 3. Completeness Fill

**Impact:** MEDIUM
**When to apply:** Missing any of: output format specification, success
criteria, or edge case handling
**When to skip:** All three are present

Add the missing elements:
- **Output format:** What shape should the response take? (list, table,
  prose, code, JSON)
- **Success criteria:** How will the user judge if the output is good?
- **Edge cases:** What should happen with unusual inputs? (empty, too large,
  malformed)

Only add what's missing. Don't over-specify what's already clear from context.

**Evidence:** Anthropic Tier 1 documentation — "Be explicit about what you
want. Claude works best when instructions are specific rather than implicit."

---

## 4. Prompt Repetition

**Impact:** HIGH (conditional)
**When to apply:** Non-reasoning context AND the prompt contains a critical
instruction that must not be ignored (e.g., format constraints, safety rules)
**When to skip:** Reasoning/thinking tasks, short prompts, or when the
critical instruction is already emphasized

Repeat the most important instruction at both the beginning and end of the
prompt. Use slight rephrasing to avoid appearing redundant.

**Evidence:** Leviathan et al. "Repeat After Me" (Google Research, Dec 2025)
— won 47/70 benchmarks, lost 0. Addresses lost-in-the-middle attention
patterns.

---

## 5. Few-Shot Examples

**Impact:** MEDIUM (conditional)
**When to apply:** The prompt requires a specific output format or tone AND
will be reused (template, skill instruction, recurring task)
**When to skip:** One-off tasks, obvious format, or when examples would make
the prompt too long for its purpose

Add 1-3 input/output examples that demonstrate the expected behavior. Choose
examples that cover:
- The typical case
- An edge case (if relevant)

Keep examples concise. Label clearly with "Example:" or `<example>` tags.

**Evidence:** Anthropic Tier 1 documentation — "Examples are the single most
reliable way to steer Claude's output format and style."

---

## 6. Self-Check Instruction

**Impact:** LOW (conditional)
**When to apply:** The output is objectively verifiable (code that should
compile, math that should be correct, facts that can be checked)
**When to skip:** Creative tasks, subjective outputs, or tasks where
self-checking would add unhelpful second-guessing

Add an instruction to verify the output before presenting it:
- "Before responding, verify that [specific check]"
- "Double-check that [constraint] is satisfied"

Be specific about what to check. Generic "review your work" adds nothing.

**Evidence:** Schulhoff et al. "The Prompt Report" (arXiv:2406.06608) —
TACL survey finds self-check works only with specific, verifiable criteria.

---

## 7. Role Assignment

**Impact:** LOW
**When to apply:** The task requires specialized domain knowledge (legal,
medical, security, specific framework expertise)
**When to skip:** General-purpose tasks, tasks where domain framing would
narrow the response unhelpfully

Assign a specific role at the start of the prompt:
- "You are a senior security engineer reviewing..."
- "You are a database performance specialist..."

Use roles that invoke specific expertise, not generic authority ("You are an
expert" adds nothing).

**Evidence:** Anthropic Tier 1 documentation — "Even a single sentence of
role context makes a measurable difference on domain-specific tasks."

---

## Excluded Techniques

These were evaluated and intentionally excluded:

| Technique | Why excluded |
|-----------|-------------|
| Chain-of-thought injection | Decreasing value on reasoning models (Claude 4.x has built-in reasoning); 20-80% latency cost (Mollick et al., Wharton 2025) |
| Self-reflection loops | Unreliable without external feedback; TACL survey shows minimal benefit |
| Meta-prompting | Handled by agent/subagent systems, not individual prompts |
```

**Step 2: Verify the file exists and check the technique count**

Run: `grep -c "^## [0-9]" skills/refine-prompt/references/technique-registry.md`
Expected: `7` (seven numbered technique sections)

**Step 3: Commit**

```bash
git add skills/refine-prompt/references/technique-registry.md
git commit -m "feat: add technique registry reference for refine-prompt (#71)"
```

---

### Task 4: Verify Skill Discovery and Run Full Tests

**Context:** Claude Code auto-discovers skills by finding `SKILL.md` files in `skills/` subdirectories. We need to verify the file structure is correct and that nothing we added breaks existing tests.

**Step 1: Verify skill directory structure**

Run: `find skills/refine-prompt -type f | sort`
Expected:
```
skills/refine-prompt/SKILL.md
skills/refine-prompt/references/assessment-rubric.md
skills/refine-prompt/references/technique-registry.md
```

**Step 2: Verify SKILL.md frontmatter has required fields**

Run: `head -12 skills/refine-prompt/SKILL.md`
Expected: Shows `name: refine-prompt`, `description:`, `argument-hint:`, `user-invocable: true`, and `references:` list

**Step 3: Run the full test suite**

Run: `uv run python -m pytest tests/ -v`
Expected: All existing tests pass (this is a skill-only change — no Python code was added, so no tests should break)

**Step 4: Run linter (if available)**

Run: `ruff check wos/ tests/ scripts/`
Expected: No errors (ruff may not be installed locally; if not, skip)

**Step 5: Commit any fixes if needed**

If anything broke, fix and commit.

---

### Task 5: Update Plan Doc and Close Out

**Files:**
- Modify: `artifacts/plans/2026-02-27-refine-prompt-plan.md` (this file — mark tasks complete)

**Step 1: Mark all tasks complete in this plan**

Check off each task's checkbox.

**Step 2: Commit**

```bash
git add artifacts/plans/2026-02-27-refine-prompt-plan.md
git commit -m "docs: mark refine-prompt plan tasks complete (#71)"
```
