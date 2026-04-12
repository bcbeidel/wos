---
name: Context Docs Anti-Patterns Update (G11 + G12)
description: Add anti-patterns #11 and #12 to instruction-file-authoring-anti-patterns.context.md and update corroborating evidence for #2 and #8, closing gaps identified in the skill curation comparative analysis
type: plan
status: executing
branch: skill-curation-comparative-analysis
pr: TBD
related:
  - docs/research/2026-04-11-skill-curation-comparative-analysis.research.md
  - docs/context/instruction-file-authoring-anti-patterns.context.md
  - docs/context/instruction-file-non-inferable-specificity.context.md
---

# Context Docs Anti-Patterns Update (G11 + G12)

**Goal:** Extend `instruction-file-authoring-anti-patterns.context.md` with two new anti-patterns (body-embedded routing guidance and L2/L3 collapse) and strengthen corroborating evidence for #2 and #8, as called out in the comparative analysis (G11, plus the progressive disclosure gaps review).

**Scope:**

Must have:
- Anti-pattern #11 (body-embedded routing guidance) added — table row + explanation paragraph
- Anti-pattern #12 (L2/L3 collapse) added — table row + explanation paragraph
- Evidence column for #2 (length bloat) updated with OpenAI Codex skill-creator and Yarmoluk guide
- Evidence column for #8 (missing negative rules) updated with WOS build-skill
- `python scripts/lint.py --root . --no-urls` passes clean after all changes
- `instruction-file-non-inferable-specificity.context.md` left untouched (confirmed no gaps)

Won't have:
- Changes to any file other than `instruction-file-authoring-anti-patterns.context.md`
- New anti-patterns beyond #11 and #12 (other gaps are addressed in separate plans)
- Changes to Python code, tests, or skills
- Evidence level downgrades on existing anti-patterns

**Approach:** Three targeted edits to a single context file, applied in sequence from least to most additive. Changes 1 and 2 (evidence column updates for #2 and #8) are minimal cell edits in the existing table. Changes 3 and 4 (new anti-patterns #11 and #12) each add one table row and one explanation paragraph, following the format established by anti-patterns #1–#10. The `updated` date in frontmatter is bumped after all edits. Lint passes before commit.

**File Changes:**
- Modify: `docs/context/instruction-file-authoring-anti-patterns.context.md`

---

## Task 1: Update evidence for existing anti-patterns #2 and #8

Edit `docs/context/instruction-file-authoring-anti-patterns.context.md`:

- **#2 (length bloat):** Replace source cell `Claude Code docs, Chroma context-rot, HumanLayer` with `Claude Code docs, Chroma context-rot, HumanLayer, OpenAI Codex skill-creator ('context window is a public good'); Yarmoluk guide`
- **#8 (missing negative rules):** Replace source cell `MindStudio, VirtusLab` with `MindStudio, VirtusLab, WOS build-skill (elicits won't-dos at creation)`

- [x] **Step 1:** Read `docs/context/instruction-file-authoring-anti-patterns.context.md` to confirm current table cell values for rows #2 and #8.
- [x] **Step 2:** Edit the Source column for row #2: append `, OpenAI Codex skill-creator ('context window is a public good'); Yarmoluk guide`
- [x] **Step 3:** Edit the Source column for row #8: append `, WOS build-skill (elicits won't-dos at creation)`
- [x] **Step 4:** Verify: `grep -A1 "Length bloat" docs/context/instruction-file-authoring-anti-patterns.context.md | grep "Yarmoluk"` → matches
- [x] **Step 5:** Verify: `grep -A1 "Missing negative rules" docs/context/instruction-file-authoring-anti-patterns.context.md | grep "build-skill"` → matches
- [x] **Step 6:** `python scripts/lint.py --root . --no-urls 2>&1 | grep "anti-patterns"` → no new warnings

---

## Task 2: Add anti-pattern #11 — body-embedded routing guidance

Edit `docs/context/instruction-file-authoring-anti-patterns.context.md`:

**Table row** (append after row #10):
```
| 11 | Body-embedded routing guidance — "When to Use This Skill" in the body | HIGH | OpenAI Codex skill-creator; WOS L1/L2/L3 architecture |
```

**Explanation paragraph** (append after the "Redundancy with project documentation" paragraph):
```
**Body-embedded routing guidance.** Any 'When to Use This Skill' section or trigger-condition guidance written in the skill body is routing-blind: the body loads only after the skill triggers, so routing guidance inside it is never evaluated at routing time. Authors who write 'Use this skill when...' in the body believe they have addressed routing; they have not. All trigger conditions, activation phrases, and use-case descriptions must appear in the `description` frontmatter field. Evidence: OpenAI Codex skill-creator explicitly prohibits this pattern; consistent with WOS's L1/L2/L3 loading model in which L1 (description) is the only pre-trigger signal.
```

- [x] **Step 1:** Read the current file to confirm end of table and end of explanation section.
- [x] **Step 2:** Add the table row for #11 after the #10 row.
- [x] **Step 3:** Add the explanation paragraph for #11 after the final existing paragraph.
- [x] **Step 4:** Verify: `grep -c "^| [0-9]" docs/context/instruction-file-authoring-anti-patterns.context.md` → outputs `12` (header row counts separately — confirm 11 data rows if needed)
- [x] **Step 5:** Verify: `grep "Body-embedded routing" docs/context/instruction-file-authoring-anti-patterns.context.md` → two matches (table row + paragraph heading)
- [x] **Step 6:** `python scripts/lint.py --root . --no-urls 2>&1 | grep "anti-patterns"` → no new warnings

---

## Task 3: Add anti-pattern #12 — L2/L3 collapse

Edit `docs/context/instruction-file-authoring-anti-patterns.context.md`:

**Table row** (append after row #11):
```
| 12 | L2/L3 collapse — embedding reference-level material in the body instead of references/ | HIGH | WOS loading model; OpenAI Codex skill-creator; Yarmoluk guide |
```

**Explanation paragraph** (append after the #11 paragraph):
```
**L2/L3 collapse.** Embedding domain documentation, schemas, lookup tables, or long examples directly in the skill body violates the progressive disclosure contract: L2 is for instructions, L3 is for reference material. Body bloat from reference content dilutes instruction density, consumes context window tokens on every invocation regardless of whether the reference is needed, and defeats lazy loading. The test: if a section of the body would be skipped for most invocations of the skill, it belongs in a named `references/` file cited from the body. Evidence: consistent across WOS architecture, OpenAI Codex skill-creator references/ guidance, and Yarmoluk's token efficiency principles (three independent convergences = HIGH).
```

- [x] **Step 1:** Confirm current state of file (row #11 and its paragraph present from Task 2).
- [x] **Step 2:** Add the table row for #12 after the #11 row.
- [x] **Step 3:** Add the explanation paragraph for #12 after the #11 paragraph.
- [x] **Step 4:** Verify: `grep "L2/L3 collapse" docs/context/instruction-file-authoring-anti-patterns.context.md | wc -l` → `2` (table row + paragraph)
- [x] **Step 5:** Verify: `grep "three independent convergences" docs/context/instruction-file-authoring-anti-patterns.context.md` → matches (HIGH justification present)
- [x] **Step 6:** `python scripts/lint.py --root . --no-urls 2>&1 | grep "anti-patterns"` → no new warnings

---

## Task 4: Bump frontmatter date and final validation

- [x] **Step 1:** Update `updated:` date in frontmatter of `docs/context/instruction-file-authoring-anti-patterns.context.md` to `2026-04-11`.
- [x] **Step 2:** Update `description:` field in frontmatter to reflect 12 anti-patterns: replace `"Ten ranked anti-patterns` with `"Twelve ranked anti-patterns` (and update the count sentence).
- [x] **Step 3:** `python scripts/lint.py --root . --no-urls` → clean (zero warnings, zero failures)
- [x] **Step 4:** Commit: `git commit -m "docs: add anti-patterns #11 and #12 to authoring context doc (G11 + L2/L3 collapse)"` <!-- sha:4318544 -->

---

## Validation

- [ ] Anti-patterns table has exactly 12 data rows: `grep -c "^| [0-9]" docs/context/instruction-file-authoring-anti-patterns.context.md` → confirms count
- [ ] `grep "Body-embedded routing" docs/context/instruction-file-authoring-anti-patterns.context.md | wc -l` → `2`
- [ ] `grep "L2/L3 collapse" docs/context/instruction-file-authoring-anti-patterns.context.md | wc -l` → `2`
- [ ] `grep "L1/L2/L3" docs/context/instruction-file-authoring-anti-patterns.context.md` → matches (anti-pattern #11 cites the loading model)
- [ ] `grep "three independent convergences" docs/context/instruction-file-authoring-anti-patterns.context.md` → matches (anti-pattern #12 HIGH justification)
- [ ] `grep "Yarmoluk" docs/context/instruction-file-authoring-anti-patterns.context.md | wc -l` → `2` (row #2 and row #12)
- [ ] `grep "build-skill" docs/context/instruction-file-authoring-anti-patterns.context.md` → matches (row #8)
- [ ] `python scripts/lint.py --root . --no-urls` → exits 0, no warnings
