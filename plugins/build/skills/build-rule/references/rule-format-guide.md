---
name: Rule Format Guide (build-rule)
description: Specification for the `.rule.md` format — frontmatter fields, body sections, scope patterns, and Intent section template
---

# Rule Format Guide

Rules are semantic enforcement documents evaluated by an LLM — they capture
patterns too nuanced for traditional linters. The toolkit uses a single
canonical format: `.rule.md` files at `docs/rules/<slug>.rule.md`.

## Table of Contents

- [Rule Categories](#rule-categories)
- [File Naming and Location](#file-naming-and-location)
- [Frontmatter](#frontmatter)
- [Body Sections](#body-sections-all-required)
- [Scope Patterns](#scope-patterns)
- [Intent Section Template](#intent-section-template)
- [Writing Effective Rules](#writing-effective-rules)

## Rule Categories

Classify the rule before drafting. Category drives the evaluator's framing.

| Category | What it enforces | Framing |
|----------|------------------|---------|
| Correctness | Code that will behave incorrectly or produce errors | Binary PASS/FAIL |
| Suspicious | Code that is probably wrong but not guaranteed | Binary PASS/FAIL |
| Security | Code that creates vulnerabilities or exposes sensitive data | Binary PASS/FAIL |
| Complexity | Code that is too complex to maintain safely | Ordinal / warn-first |
| Performance | Code patterns with measurable performance cost | Ordinal / warn-first |
| Convention/Style | Project-specific naming, structure, or formatting conventions | Ordinal / warn-first |
| Accessibility | Code that creates accessibility barriers | Binary PASS/FAIL |
| LLM Directive | AI response-generation behavior (not code correctness) | Binary PASS/FAIL |

Category is drafting-time guidance — the rule file does not record it as a
field. The LLM evaluator infers the framing from the criterion phrasing.

---

## File Naming and Location

Stored at `docs/rules/<slug>.rule.md`. Derive the slug from the rule name:
lowercase, hyphens, no dates.

Example: "Staging Layer Purity" → `docs/rules/staging-layer-purity.rule.md`.

If `docs/rules/` does not exist, create it on write.

---

## Frontmatter

```yaml
---
name: Staging layer purity
description: Staging models must only cast, rename, and deduplicate — no business logic
scope: "models/staging/**/*.sql"
---
```

### Required Fields

| Field | Type | Purpose | Consumed by |
|-------|------|---------|-------------|
| `name` | string | Human-readable rule name | check-rule (concern-prefix); LLM evaluator |
| `description` | string | One-sentence summary of what the rule enforces | check-rule (specificity); LLM evaluator at trigger time |
| `scope` | string or list | Glob pattern(s) matching files this rule applies to | check-rule (conflict overlap, glob validity); LLM evaluator scopes itself by it |

Every prescribed field has a consumer. The `.rule.md` extension already
disambiguates the file type — no `type:` tag is needed.

---

## Body Sections (all required)

**`## Intent`** — explains WHY this rule exists. Not what it checks — why it
matters. See the Intent Section Template for the four required components.

**`## Non-Compliant Example`** — shown FIRST. What a violation looks like. Use
actual code snippets from the codebase, not synthetic examples.

**`## Compliant Example`** — what correct code looks like.

Non-compliant before compliant: listing exclusions first improves LLM
classification accuracy.

---

## Scope Patterns

```yaml
# Single pattern
scope: "models/staging/**/*.sql"

# Multiple patterns
scope:
  - "src/api/**/*.py"
  - "src/handlers/**/*.py"
```

- Be specific. `**/*.py` fires on every Python file — almost always too broad.
- Use directory prefixes to target architectural layers.
- Test the scope mentally: list which files match and confirm the rule
  applies to ALL of them.

---

## Intent Section Template

Every rule's Intent section must contain four components. Use this template:

```markdown
## Intent

[VIOLATION: what pattern does this rule catch?]
[FAILURE COST: what specifically goes wrong when this pattern occurs, and who bears it?]
[PRINCIPLE: what underlying value does this enforce — type safety, security, maintainability?]
Exception: [EXCEPTION POLICY: name at least one case where disabling this rule is legitimate].
When evidence is borderline, prefer WARN over PASS.
```

**Weak Intent (do not publish):**
> "Avoid using `console.log` in production code. It creates noise."

Problems: names violation only, no failure cost, no principle, no exception
policy.

**Strong Intent:**
> "`console.log` in production builds exposes internal state to end users
> via browser developer tools, and adds measurable latency in high-frequency
> call paths. This enforces the principle that production code does not leak
> implementation details. Exception: `console.error` for critical runtime
> errors where structured logging is unavailable. When evidence is
> borderline, prefer WARN over PASS."

---

## Writing Effective Rules

**Classify before drafting.** Use the Rule Categories table to set the
evaluator's binary/ordinal framing before writing.

**Start narrow, add exclusions.** Draft the rule to match your known failure
case. Broaden only after validating against known negative examples. A rule
that fires twice with 100% accuracy is more valuable than one that fires 200
times with 50%.

**One convention per rule.** If the description contains "and", it's probably
two rules. Split them.

**Examples from real code.** Use actual code snippets with file path comments
(`// path/to/file.ext`). Synthetic examples with generic identifiers (foo,
bar, myFunction) are weaker anchors.

**Default-closed stance.** Every rule must define how uncertain or borderline
cases resolve. "When evidence is borderline, surface as WARN rather than
PASS." If this isn't specified, models default to PASS, hiding real
violations.

**Test the ambiguity.** Ask: would two experienced developers independently
agree whether a given file passes or fails? If not, the rule needs more
specific examples or a narrower scope.
