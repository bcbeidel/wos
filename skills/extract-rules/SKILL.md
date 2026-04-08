---
name: extract-rules
description: Surfaces and captures codebase conventions as structured rule files. Use when the user wants to "create a rule", "extract a rule", "capture this convention", "enforce this pattern", or describes a convention they want enforced.
argument-hint: A description of the convention, file paths to exemplary code, or a link to an external style guide
user-invocable: true
references:
  - references/rule-format-guide.md
---

# /wos:extract-rules

Extract codebase conventions into structured rule files in `docs/rules/`.
Rules are evaluated by Claude for semantic compliance — they handle
patterns too nuanced for traditional linters.

## Workflow

### 1. Detect Mode

Determine the extraction mode from the user's input:

| Input | Mode |
|-------|------|
| User describes a convention in words | **conversation** |
| User points to files or code examples | **from-code** |
| User provides a style guide, RFC, or external doc | **from-source** |

If ambiguous, ask: "Would you like to describe the rule, point me at
exemplary code, or provide a reference document?"

### 2. Gather Rule Details

**Conversation mode:**
- Ask clarifying questions one at a time, multiple-choice preferred
- Establish: what the rule enforces, which files it applies to (scope),
  how strict it is (severity), and why it exists (intent)
- Default severity to `warn` unless the user specifies `fail`

**From-code mode:**
- Read the exemplary files the user identified
- Infer the convention: what pattern do these files share?
- Propose the rule with examples drawn directly from the actual code
- Ask the user to confirm or refine the inferred convention

**From-source mode:**
- Read the provided document (style guide, RFC, wiki page)
- Identify enforceable conventions — statements that can produce a
  clear pass/fail judgment on a single file
- Present candidate rules as a numbered list
- User selects which to keep

### 3. Draft the Rule

Compose a rule file following the [Rule Format Guide](references/rule-format-guide.md).

Required elements:
- **Frontmatter:** name, description, type (`rule`), scope (glob pattern),
  severity (`warn` or `fail`)
- **Intent:** 1-2 sentences explaining WHY this rule exists
- **Non-compliant example:** shown FIRST — what a violation looks like
- **Compliant example:** what correct code looks like

Research shows non-compliant examples placed before compliant examples
improve classification accuracy. Both examples serve as concrete anchors
that disambiguate intent far more effectively than additional prose.

### 4. Check for Duplicates

Before writing, read existing rules in `docs/rules/`:
- Check for rules with overlapping scope globs
- Check for rules with similar names or descriptions
- If overlap found, present to user: "This overlaps with [existing rule].
  Merge, replace, or keep both?"

### 5. Present for Approval

Show the complete rule file to the user. Do not write until approved.

### 6. Write the Rule

- Create `docs/rules/` directory if it doesn't exist
- Write the rule file as `docs/rules/<slug>.rule.md`
- Derive the slug from the rule name (lowercase, hyphens)

## Key Instructions

- Every rule MUST have both a non-compliant and compliant example.
  Rules without examples produce unreliable enforcement.
- Default severity is `warn`. Only use `fail` when the user explicitly
  requests it or the convention is a hard constraint.
- Scope patterns should be as specific as possible. Broad scopes
  (e.g., `**/*.py`) cause rules to fire on irrelevant files,
  increasing false positives and eroding trust.
- Rules should target semantic conventions that traditional linters
  cannot catch — layer boundaries, architectural constraints,
  naming intent, documentation quality.
- One convention per rule. If a user describes multiple conventions,
  create separate rule files.

## Anti-Pattern Guards

1. **Rules without examples** — refuse to write. Examples are the single
   highest-leverage addition to any rule (4x reliability improvement).
2. **Overly broad scope** — flag and suggest narrowing. `**/*` is almost
   never correct.
3. **Rules that a linter handles better** — suggest the appropriate linter
   instead. LLM-based rules are for semantic understanding, not syntax.
4. **Multiple conventions in one rule** — split into separate rules.
   One rule, one convention.
