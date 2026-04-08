---
name: Rule Extraction and Enforcement
description: System for extracting codebase conventions into structured rule files and enforcing them via LLM-based semantic evaluation
type: design
status: draft
related:
  - docs/research/2026-04-07-effective-rules-for-llm-enforcement.research.md
---

## Purpose

A rule extraction and enforcement system for WOS. Users extract implicit
codebase conventions into structured rule files. Rules are enforced
automatically via Claude Code hooks that evaluate changed files against
applicable rules using LLM-based semantic understanding.

Two skills:
- `/wos:extract-rules` — surfaces conventions from code, conversations,
  or external sources and writes them as rule files
- `/wos:check-rules` — validates files against applicable rules
  (invocable on-demand, also wired into hooks)

## Rule Format

Each rule is a standalone markdown file in `docs/rules/` with structured
frontmatter:

```yaml
---
name: Staging layer purity
description: Staging models must only cast, rename, and deduplicate — no business logic
type: rule
scope: "models/staging/**/*.sql"
severity: fail
---
```

Body contains three required sections:

1. **Intent** — why this rule exists (1-2 sentences). Research shows
   enforcement without education causes developers to bypass rules [27].
2. **Compliant example** — what correct code looks like
3. **Non-compliant example** — what a violation looks like

Key fields:

- `scope` — glob pattern (required). Multiple patterns as a list for
  broader rules. Determines which files the rule applies to. Scope
  precision directly reduces triggering errors — LLM performance degrades
  as irrelevant rules increase [1].
- `severity` — `warn` (advisory, default) or `fail` (blocks). Defaults
  to `warn` because false positives erode trust faster than false
  negatives [25, 26].
- Examples are **required** — context-specific rubrics improve evaluation
  reliability by 4x (Cohen's Kappa 0.156→0.646) [8]. Both compliant and
  non-compliant examples serve as concrete anchors. Place the
  non-compliant example first (exclusions before inclusions improves
  classification accuracy) [2].

`docs/rules/` has a standard `_index.md` like other WOS areas.

## Extraction Behavior (`/wos:extract-rules`)

The skill takes a user-described convention and produces a rule file.
Three modes:

1. **From conversation** — user describes a pattern ("staging models
   should only cast and rename"). The skill asks clarifying questions
   (scope, severity, examples), then writes the rule file.

2. **From code** — user points at exemplary files ("these staging models
   are the pattern I want enforced"). The skill reads them, infers the
   convention, proposes a rule with examples drawn from the actual code,
   and confirms with the user before writing.

3. **From external source** — user provides a style guide, RFC, or doc.
   The skill distills enforceable rules from it, presents candidates,
   and the user picks which to keep.

In all modes, the skill:

- Proposes the rule and presents it for approval before writing
- Generates both compliant and non-compliant examples when possible
- Defaults severity to `warn` unless the user specifies otherwise
- Checks for overlap with existing rules in `docs/rules/` to avoid
  duplication

## Enforcement Behavior (`/wos:check-rules`)

Two enforcement paths:

**On-demand** — user invokes `/wos:check-rules` with optional file path
or directory. The skill:

1. Discovers all rule files in `docs/rules/`
2. Matches rules to target files by `scope` glob
3. For each matched rule+file pair, Claude evaluates compliance using
   the rule's intent and examples
4. Reports results grouped by file: pass, warn, or fail with explanation

**Automatic (hooks)** — a pre-commit or file-save hook that runs the
same check against changed files only. The skill provides a setup
command to wire the hook into Claude Code's `settings.json`.

### Evaluation Approach

Each rule is evaluated independently. One rule, one file, one verdict.
No chaining, no cross-file analysis. This aligns with Anthropic's
guidance to grade dimensions separately [12] and avoids the 150-200
instruction limit that degrades multi-rule prompts [4, 7].

**Evaluation prompt structure** (research-informed):

1. The full rule file is included **verbatim** in the evaluation prompt —
   never summarized. This implements the "locked rubric" pattern that
   prevents interpretation drift across evaluations [15].
2. The LLM must produce **chain-of-thought reasoning before the verdict**.
   Structured reasoning before judgment improves accuracy by 10-15
   percentage points [3, 16].
3. Output is **binary pass/fail** with an explanation. Binary evaluation
   is more reliable than graded scales for objective compliance tasks
   [11, 17].

```
Given this rule:
[full rule file content]

And this file:
[file content]

First, reason through whether this file complies with the rule.
Consider the intent, compliant example, and non-compliant example.
Then provide your verdict.

Output:
- reasoning: [your analysis]
- verdict: PASS or FAIL
- explanation: [one sentence if FAIL, explaining what violates and why]
```

### Output Format

```
PASS  models/staging/orders.sql — Staging layer purity
FAIL  models/staging/customers.sql — Staging layer purity
  "Contains revenue calculation logic — move to marts layer"
```

### Cost and Latency

Every rule x file pair is an LLM call. For large changesets with many
rules, this could be slow. Scope globs are the primary throttle —
well-scoped rules only fire on relevant files.

## Research (Completed)

See [Effective Rules for LLM Enforcement](../research/2026-04-07-effective-rules-for-llm-enforcement.research.md)
for the full investigation (27 sources, 5 sub-questions). Key findings
that shaped this design:

- Context-specific rules improve evaluation reliability by 4x [8]
- Examples are the single highest-leverage addition to any rule [6]
- Binary pass/fail with chain-of-thought is the most reliable
  evaluation mode [3, 11, 16, 17]
- False positives erode trust faster than false negatives — default
  to `warn` [25, 26, 27]
- Rule count per prompt has hard limits (~150-200 instructions) —
  scope-based matching is essential [4, 7]
- The rule file itself serves as the locked rubric — include verbatim,
  never summarize [15]
- LLM-based enforcement complements deterministic linting, does not
  replace it [7]

## Rule Templates

A standard library of common rules that users can adopt and customize.
Categories to cover:

- **Naming conventions** — file naming, variable naming, module naming
- **Layer boundaries** — separation of concerns, forbidden imports,
  data flow direction
- **Test requirements** — coverage expectations, test file placement,
  test naming
- **Documentation** — required sections, frontmatter fields, changelog
  updates
- **Code organization** — module boundaries, dependency direction,
  public API surface

Templates ship with WOS and are copied into the user's `docs/rules/`
when adopted, allowing full customization. This follows the dominant
pattern across rule ecosystems (ESLint shareable configs, Semgrep
registries, dbt packages) [19, 20, 22].

**Template design principles** (research-informed):
- Start with a small, high-confidence set — expand methodically [21]
- Every template must include compliant and non-compliant examples
  (Semgrep requires at least one true positive and one true negative
  for every contributed rule) [20]
- Organize by concern (naming, boundaries, tests, docs), not by
  language or technology [Biome, Ruff pattern]
- Templates are self-documenting: intent explains why, examples show
  what, scope makes applicability explicit

## Positioning

LLM-based rule enforcement is **complementary to deterministic linting**,
not a replacement. Traditional linters (ESLint, Ruff, SQLFluff) excel at
syntax and pattern matching. LLM-based evaluation excels at semantic
understanding — rules like "no business logic in the staging layer" that
require judgment, not pattern matching.

The system should be positioned for rules that are:
- Too semantic for regex/AST matching
- Context-dependent (what's "business logic" varies by project)
- Architectural (layer boundaries, separation of concerns)
- Convention-based (naming intent, documentation quality)

## Scope Boundaries

**Must have:**

- Rule file format with frontmatter (name, description, scope, severity)
- `/wos:extract-rules` skill — all three source modes
- `/wos:check-rules` skill — on-demand invocation
- `docs/rules/` area with `_index.md` integration
- Hook setup guidance
- Research into rule effectiveness
- Rule templates (standard library of common rules)

**Won't have (for now):**

- Rule versioning or changelog
- Cross-file rules (e.g., "if A exists, B must also exist")
- Auto-fix / remediation suggestions
- CI integration script

## Acceptance Criteria

1. A user can invoke `/wos:extract-rules`, describe a convention, and
   get a well-formed rule file in `docs/rules/`
2. A user can point at exemplary code and have a rule inferred from it
3. `/wos:check-rules` evaluates changed files against matching rules
   and reports pass/warn/fail with explanations
4. Rules with examples produce more consistent enforcement than rules
   without (validated by research)
5. Template rules can be adopted into a project with a single command
6. Hook setup instructions enable automatic enforcement on commit
