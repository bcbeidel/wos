---
name: build-rule
description: Create a correctly-structured rule for LLM-based semantic enforcement. Use when the user wants to "create a rule", "build a rule", "add a rule", "capture this convention", or "enforce this pattern".
argument-hint: A code pattern, behavior description, or existing rule draft to formalize
user-invocable: true
references:
  - references/rule-format-guide.md
  - ../../_shared/references/primitive-routing.md
---

# /build:build-rule

Create semantic enforcement rules that Claude evaluates for compliance.
Rules capture conventions too nuanced for traditional linters — architectural
boundaries, naming intent, layer purity, documentation quality.

Every rule requires both a non-compliant and compliant example from real code.
Won't write a rule without both.

## Workflow

### 0. Verify Primitive

Before proceeding, confirm a rule is the right mechanism. Full decision matrix: [primitive-routing.md](../../_shared/references/primitive-routing.md).

**Not right — redirect instead:**
- Check is shell-expressible (grep, file existence, regex) → recommend a hook or linter
- Enforcement must fire at a lifecycle event (pre-commit, pre-tool-use) → redirect to `/build:build-hook`
- Convention is procedural (multi-step workflow Claude should follow) → redirect to CLAUDE.md or `/build:build-skill`

**A rule is right when:** enforcement requires LLM judgment on static file content and the convention is too nuanced for grep or an AST linter. Proceed only when this holds.

### 1. Resolve Path

Rule files live at `docs/rules/<slug>.rule.md`. Derive the slug from the
rule name (lowercase, hyphens, no dates) and confirm the directory exists
(create on write if not). One canonical format keeps discovery, audit,
and conflict detection simple.

### 2. Classify Rule Type

Before eliciting the pattern, determine the rule category. Present the eight categories and ask which best describes the rule:

| Category | What it enforces |
|----------|-----------------|
| **Correctness** | Code that will behave incorrectly or produce errors |
| **Suspicious** | Code that is probably wrong but not guaranteed |
| **Security** | Code that creates vulnerabilities or exposes sensitive data |
| **Complexity** | Code that is too complex to maintain safely |
| **Performance** | Code patterns with measurable performance cost |
| **Convention/Style** | Project-specific naming, structure, or formatting conventions |
| **Accessibility** | Code that creates accessibility barriers |
| **LLM Directive** | AI response-generation behavior (not code correctness) |

Category drives the evaluator's framing:
- **Binary PASS/FAIL** for Correctness, Suspicious, Security, Accessibility, LLM Directive
- **Ordinal / warn-first** for Complexity, Performance, Convention/Style

### 3. Elicit Pattern

Treat `$ARGUMENTS` as the user's initial input — a code pattern, behavior
description, or existing rule draft. If `$ARGUMENTS` is empty, prompt for
one of those three intake modes. Determine the intake mode from
`$ARGUMENTS`:

| Input | Mode |
|-------|------|
| User describes a convention | **conversation** |
| User points to files or code | **from-code** |
| User provides style guide or RFC | **from-source** |

**Conversation mode:**
- Ask clarifying questions one at a time, multiple-choice preferred
- Establish: what the rule enforces, which files (scope), and why (intent)

**From-code mode:**
- Read the exemplary files the user identified
- Identify the shared pattern; propose with examples from actual code
- Ask the user to confirm or refine

**From-source mode:**
- Read the provided document; identify enforceable statements
- Present candidate rules as a numbered list; user selects

If the user describes something a traditional linter handles (syntax, formatting,
import ordering), recommend the appropriate linter tool instead.

### 4. Check for Conflicts

Before drafting, read existing rules in the project:
- Check for rules with overlapping scope globs
- Check for rules with similar names or descriptions
- If overlap found: "This overlaps with [existing rule]. Merge, replace, or keep both?"

Do not skip this step. Undetected conflicts create contradiction in the rule
library and degrade enforcement reliability.

### 5. Draft Rule

Compose the rule following the [Rule Format Guide](references/rule-format-guide.md).

Required:
- **Intent** — WHY this rule exists; must contain all four components (see below)
- **Non-compliant example** — shown FIRST; drawn from actual codebase code
- **Compliant example** — what correct code looks like

**Intent four-component requirement.** The Intent section must contain:
1. **Violation** — what pattern does this rule catch?
2. **Failure cost** — what specifically goes wrong, and who bears it? (load-bearing — do not omit)
3. **Principle** — what underlying value does this enforce (type safety, security, maintainability)?
4. **Exception policy** — when is disabling legitimate? Name at least one case. (load-bearing — do not omit)

Non-compliant before compliant: listing exclusions first improves classification
accuracy. Use actual code snippets with file path comments — synthetic examples
with generic identifiers (foo, bar, myFunction) produce weaker anchors.

### 6. Validate Structure

Before presenting, self-check against all ten criteria. Fix any gap before presenting.

**Three structural requirements** (see [rule-format-guide.md](references/rule-format-guide.md) — *Writing Effective Rules*):
1. **Specificity** — all key terms have explicit behavioral definitions; no vague words like "good", "clean", "clear", "appropriate"
2. **Scale matching** — binary PASS/FAIL for this rule type (not 1-5 or percentage). *Drafting-time only — the rule file does not record its scale, so check-rule cannot independently verify it.*
3. **Scope isolation** — exactly one convention; no "and" in the description

**Four linter patterns** (audited by check-rule — see [audit-dimensions.md](../check-rule/references/audit-dimensions.md)):
4. **Behavioral anchoring** — both examples demonstrate observable, citable behaviors
5. **Meta/create separation** — criterion defined separately from evaluation context (Intent section exists and explains the criterion, not the enforcement mechanism)
6. **Start-narrow** — scope targets the specific file pattern where the known failure occurs; not `**/*` or `**/*.ext` without directory prefix
7. **Default-closed** — rule declares how uncertain cases resolve (WARN, not PASS)
8. **Concern-prefix** (if library has >5 rules) — rule name prefixed by domain (e.g., `quality-`, `safety-`, `compliance-`, `style-`)

**Two Intent / example quality checks** (audited by check-rule Dim 4–5; research grounding in [.research/rule-best-practices.md](../../../../.research/rule-best-practices.md)):
9. **Intent completeness** — Intent section contains all four components: violation, failure cost, principle, exception policy; no weak signals present (hedging language, prohibition-without-consequence, no exception policy)
10. **Example realism + single canonical example** — examples have file path comments or domain-specific identifiers, and each section contains one canonical instance (not multiple risking conflicting signals)

### 7. Present for Approval

Before showing the complete file, narrate the design choices in 3–6
bullets so the user can disagree with any structural decision before it
gets written:

- **Category and framing** — name the category picked in Step 2 and whether
  it pushed the rule toward binary PASS/FAIL or ordinal warn-first framing.
- **Scope choice** — which directory the glob targets and why (start-narrow
  rationale).
- **Intent components** — confirm all five are present; call out which
  exception case was named.
- **Example sourcing** — real codebase code or constructed; file path
  comments included.
- **What was skipped and why** — patterns considered but rejected (e.g.,
  "did not split into two rules — single criterion holds even though
  description mentions 'X and Y'; the 'and' is descriptive, not a second
  criterion").

Then show the complete rule file. Iterate on feedback. Hold the write
until the user approves.

### 8. Write the Rule

- Create `docs/rules/` if it doesn't exist
- Write the rule file at `docs/rules/<slug>.rule.md`
- Report the file path

## Example

<example>
User: "I want staging models to only do casts, renames, and deduplication"

Assistant resolves path to `docs/rules/staging-layer-purity.rule.md`. Classifies rule type: Convention/Style
(enforcing architectural layer purity). Fix-safety default: requires-review. Framing: warn-first.
Asks: "Which files should this apply to?"
User: "models/staging/**/*.sql". Asks: "Should violations block (fail) or just warn?"
User: "warn". Checks existing rules — no overlap found.

Drafts:

```yaml
---
name: Staging layer purity
description: Staging models must only cast, rename, and deduplicate — no business logic
scope: "models/staging/**/*.sql"
---
```

```markdown
## Intent

Staging models that include business logic (revenue calculations, tier
classifications) couple source schema changes to business definitions,
requiring coordinated updates across both layers when either changes.
This enforces the principle that staging models are a clean interface
over raw sources — not a transformation layer. Exception: calculated
fields that are pure data-type normalization (e.g., parsing a date
string to a date type) are permitted. When evidence is borderline,
prefer WARN over PASS.

## Non-Compliant Example

```sql
-- models/staging/stg_orders.sql
select id, quantity * unit_price as revenue,
  case when lifetime_value > 1000 then 'high' else 'standard' end as tier
from {{ source('raw', 'orders') }}
```

Violations: revenue calculation and tier classification are business logic.

## Compliant Example

```sql
-- models/staging/stg_orders.sql
select id as order_id, cast(order_date as date) as order_date,
  cast(quantity as integer) as quantity
from {{ source('raw', 'orders') }}
qualify row_number() over (partition by id order by _loaded_at desc) = 1
```

Only casts, renames, and deduplication.
```

Validates all 10 criteria — passes. Presents for approval. On approval, writes
`docs/rules/staging-layer-purity.rule.md`.
</example>

## Key Instructions

- Won't write a rule that lacks both a non-compliant and a compliant example — examples improve enforcement reliability ~4×, so the gate is hard. *(scope boundary)*
- Won't replace a traditional linter — if the request is syntax, formatting, import ordering, or naming case, redirect to the appropriate linter and stop. *(scope boundary)*
- Require all four Intent components before drafting (violation, failure cost, principle, exception policy) — failure cost (#2) and exception policy (#4) are load-bearing because their absence drives developers to disable rules rather than fix code.
- Start narrow on scope — target the specific known-failure pattern; broaden only after validating against negative examples.
- Declare a default-closed stance ("prefer WARN over PASS when borderline") in every Intent — without it, evaluators silently default to PASS and hide violations.
- Run the conflict check (Step 4) before drafting — undetected contradictions degrade the entire rule library.
- Hold the write until the user approves the drafted rule (Step 7 gate).

## Anti-Pattern Guards

1. **Rule with only one example side** — refuse to write; require both non-compliant and compliant examples (improves enforcement reliability ~4×)
2. **Glob without a directory prefix** (`**/*` or `**/*.ext`) — narrow to the architectural layer named in Intent before accepting the rule
3. **Multiple conventions packed into one rule** — any "and" in the description is a split signal; produce two rules instead
4. **Convention enforceable by a traditional linter** (syntax, formatting, import ordering) — redirect to the linter and stop
5. **Intent without a default-closed declaration** — append "When evidence is borderline, prefer WARN over PASS" so uncertain cases surface as WARN, not silently PASS
6. **Conflict check skipped** — run Step 4 before drafting; undetected contradictions in the rule library produce unpredictable enforcement
7. **Intent that states only what the rule catches** — add failure cost, principle, and exception policy so the rule educates rather than mandates blindly

## Handoff

**Receives:** Code pattern, behavior description, or existing rule draft to formalize
**Produces:** Rule file written to `docs/rules/<slug>.rule.md`
**Chainable to:** check-rule (verify the new rule fits the existing library without conflicts)