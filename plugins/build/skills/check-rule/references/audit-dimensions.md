---
name: Audit Rule Dimensions
description: Evaluation criteria for auditing a Claude Code `.claude/rules/` library — Tier-1 deterministic format checks, Tier-2 two-dimension semantic rubric, and Tier-3 cross-rule conflict detection.
---

# Audit Rule Dimensions

Rule auditing uses a three-tier hierarchy: deterministic checks first
(no LLM), then semantic evaluation (one LLM call per rule, locked rubric),
then cross-rule conflict detection (separate LLM pass over rule pairs that
could co-fire).

Handle deterministic checks (file location, glob syntax, file size) with
code-style grep/read — faster, cheaper, and more reliable than asking the
LLM to parse them.

## Table of Contents

- [Category Tiers](#category-tiers)
- [Tier 1: Deterministic Format Checks](#tier-1-deterministic-format-checks)
- [Tier 2: Semantic Dimensions (One LLM Call per Rule)](#tier-2-semantic-dimensions-one-llm-call-per-rule)
  - [Dimension 1: Specificity](#dimension-1-specificity)
  - [Dimension 2: Single Concern](#dimension-2-single-concern)
- [Evaluation Prompt Template](#evaluation-prompt-template)
- [Tier 3: Cross-Rule Conflict Detection](#tier-3-cross-rule-conflict-detection)
- [Output Format](#output-format)

---

## Category Tiers

Every check carries a category tier so users can distinguish spec-backed
findings from house-style guidance.

| Tier | Meaning |
|------|---------|
| **canonical** | Enforces a documented Anthropic rule for `.claude/rules/` (location, extension, `paths:` field) |
| **research-grounded** | Toolkit-opinion check whose design is supported by published research (cited in `.research/rule-best-practices.md`) |
| **toolkit-opinion** | Recommended by this toolkit; no upstream spec |

The tier appears in parentheses after each dimension heading.

---

## Tier 1: Deterministic Format Checks

Run for every rule file before any LLM evaluation. Emit findings
immediately. Rules with FAIL findings are excluded from Tier 2.

| Check | Category | Condition | Severity |
|-------|----------|-----------|----------|
| Location | canonical | File is not under `.claude/rules/` or `~/.claude/rules/` (Claude Code does not load rules from other paths) | fail |
| Extension | canonical | File extension is not `.md` (e.g., `.rule.md`, `.mdx`, `.markdown`) | fail |
| `paths:` glob validity | canonical-mirror | `paths:` is present but a glob has unmatched brackets, invalid wildcards, or empty pattern. Mirrors check-skill's `paths` validity check. | fail |
| File size | research-grounded | File exceeds 200 non-blank lines (Anthropic's CLAUDE.md guidance applies analogously — larger rules consume context and reduce adherence) | warn |
| Frontmatter shape | toolkit-opinion | Frontmatter contains top-level keys other than `paths:` — Anthropic documents only `paths:`; unknown keys are inert at best | info |

### Notes

- **Location check:** the project's `.claude/rules/` and the user's
  `~/.claude/rules/` are the only canonical locations. Files at `docs/rules/`,
  project root, or other paths are not picked up by Claude Code.
- **Glob validity:** parse each glob in `paths:` with the same logic
  check-skill uses for `paths:` on skills — both fields share the
  same Anthropic semantics.
- **Size warning:** the 200-line threshold mirrors Anthropic's CLAUDE.md
  guidance. Rules above this should be split into topic files.

---

## Tier 2: Semantic Dimensions (One LLM Call per Rule)

Present both dimensions as a locked rubric in a single call per rule.
Include the full rule file verbatim — never summarize.

**Per-dimension calls are an anti-pattern.** Per-criterion separate calls
score 11.5 points lower on average (Hong et al., 2026, RULERS). Present
both simultaneously; score each independently within the same call.

For each dimension, produce: **verdict** (WARN or PASS), **evidence**
(specific text from the rule that triggered the verdict), and
**recommendation** (what to change). Default-closed: when evidence is
borderline, surface as WARN, not PASS.

### Dimension 1: Specificity

*(canonical — Anthropic's "Write effective instructions" guidance: "Use 2-space indentation" passes; "Format code properly" fails)*

**What it checks:** Whether the rule's directives are concrete enough
that a developer (or Claude) can verify compliance unambiguously.

**Fail signals (→ WARN):**
- Anchor-free terms used as the directive: "good", "clean", "clear",
  "appropriate", "well-structured", "properly", "nice", "consistent"
  without a behavioral definition
- Directives that defer the decision back to the reader ("use your
  judgment", "as appropriate") without a fallback rule

**Pass signals:**
- Directives are verifiable: a numeric threshold, a named tool to run,
  a specific file path or command, a quoted code pattern
- Anchor-free terms appear only when paired with a verifiable
  definition ("clean code: no functions over 50 lines, no nested
  ternaries")

**Canonical Repair:** Replace each anchor-free term with a verifiable
directive. Examples:
- "Format code properly" → "Use 2-space indentation; run `prettier --check`"
- "Test your changes" → "Run `npm test` before committing"
- "Keep files organized" → "API handlers live in `src/api/handlers/`"

### Dimension 2: Single Concern

*(toolkit-opinion — one topic per file; mirrors Anthropic's "split larger CLAUDE.md into topic-specific rules")*

**What it checks:** Whether the rule covers a single topic. A file
that mixes unrelated conventions is two rules, not one.

**Fail signals (→ WARN):**
- Multiple top-level `##` sections covering distinct topics that
  wouldn't naturally co-evolve (e.g., "API conventions" and
  "Test conventions" in the same file)
- Filename describes one topic but body covers another in addition
- Two unrelated `paths:` patterns where each `##` section applies to
  only one (split signal)

**Pass signals:**
- All `##` sections relate to the topic named in the filename
- `paths:` globs all target files where every directive in the body
  applies

**Canonical Repair:** Split into separate topic files. Move each
unrelated section to its own `<topic>.md` under `.claude/rules/`.
Update `paths:` if the original was a union covering multiple file
types — each split file gets the subset that actually applies.

---

## Evaluation Prompt Template

Use this skeleton for every Tier-2 LLM call. Criterion statements and
anchor examples come from the rubric above — do not generate them
per-audit.

```
You are auditing a Claude Code rule file. Evaluate both dimensions
below in a single response.

For each dimension:
1. Quote the specific text from the rule that is most relevant (evidence)
2. Explain your reasoning
3. State your verdict: WARN or PASS
4. Give a specific Recommendation if WARN (name the exact change)

When evidence is borderline, surface as WARN, not PASS.

---

## Dimension 1: Specificity
Criterion: Are the rule's directives verifiable? A directive is
verifiable when a reader can check compliance without subjective
judgment — a numeric threshold, a named command, a quoted code
pattern, or a specific file path.

PASS anchor: "Use 2-space indentation; run `prettier --check` before committing"
FAIL anchor: "Format code properly and keep files organized"

## Dimension 2: Single Concern
Criterion: Does the rule cover one topic? A rule covers one topic
when every `##` section in the body advances the same convention,
and (if `paths:` is present) every glob targets files where every
directive applies.

PASS anchor: filename `api-handlers.md`, all sections about API handler conventions, `paths: "src/api/**/*.ts"`
FAIL anchor: filename `conventions.md`, sections cover API design AND test naming AND deployment process

---

<rule file verbatim>

---

Output format (one block per dimension):
## Dimension N: [Name]
Evidence: "[quoted text from rule]"
Reasoning: [your reasoning]
Verdict: WARN | PASS
Recommendation: [specific change if WARN, else "None"]
```

---

## Tier 3: Cross-Rule Conflict Detection

Run after per-rule semantic evaluation. Compare rule pairs that could
co-fire.

**A pair can co-fire when:**
- Both rules are always-on (no `paths:`), OR
- Their `paths:` globs share at least one matching file

**A conflict exists when:** following one rule's directives as written
would cause a developer to violate the other rule.

**Evaluation prompt for each rule pair:**
1. Present Rule A verbatim
2. Present Rule B verbatim
3. Ask: "If a developer follows Rule A's directives exactly, does Rule
   B's guidance contradict?"
4. Ask the reverse
5. If either answer is yes → FAIL finding for both rules

**Output format for conflicts:**
```
FAIL  .claude/rules/rule-a.md — Conflicts with rule-b.md
  "Rule A says X; Rule B says not-X"
FAIL  .claude/rules/rule-b.md — Conflicts with rule-a.md
  "Rule B says not-X; Rule A says X"
```

Anthropic's basis: *"if two rules contradict each other, Claude may
pick one arbitrarily."*

---

## Output Format

All findings use the `scripts/lint.py` format:

```
FAIL  .claude/rules/api-handlers.md — Malformed paths glob: unclosed brace
WARN  .claude/rules/code-style.md — Specificity: "format code properly" is anchor-free
WARN  .claude/rules/testing.md — File length 287 lines exceeds 200-line guidance
```

Sort order: FAIL findings first, WARN findings second; within each
severity, Tier-1 deterministic findings first, then Tier-2 dimensions
in numerical order (Specificity → Single Concern), then Tier-3
conflicts; ties break alphabetically by file path.

Final summary line: `N rules audited, M findings (X fail, Y warn)` or
`N rules audited — no findings`.
