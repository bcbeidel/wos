---
name: Rule Repair Playbook (check-rule)
description: Per-failure-mode repair strategies for check-rule findings against `.claude/rules/` files — canonical fixes for Tier-1 deterministic findings, Tier-2 specificity / single-concern findings, and Tier-3 conflicts.
---

# Rule Repair Playbook

Every check-rule finding maps to a canonical repair. Before applying
any repair, state the original intent explicitly: **"This rule
guides Claude to [original directive]."** Verify the proposed repair
preserves that guidance. If the repair would change what Claude is
told to do (not just how the directive is phrased), flag it as
requiring human review before applying.

## Table of Contents

- [Tier 1: Deterministic Format Repairs](#tier-1-deterministic-format-repairs)
- [Tier 2 — Dimension 1: Specificity](#tier-2--dimension-1-specificity)
- [Tier 2 — Dimension 2: Single Concern](#tier-2--dimension-2-single-concern)
- [Tier 3: Conflicts](#tier-3-conflicts)

---

## Tier 1: Deterministic Format Repairs

### Wrong Location

**Signal:** Rule file lives outside `.claude/rules/` (e.g., `docs/rules/`, project root, `rules/` without `.claude/` prefix)

**CHANGE:** Move the file under `.claude/rules/`
**FROM:** `docs/rules/api-handlers.md`
**TO:** `.claude/rules/api-handlers.md`
**REASON:** Claude Code only auto-loads rules from `.claude/rules/` (and `~/.claude/rules/` for user rules). Files at other paths are inert — Claude never reads them as rules.

### Wrong Extension

**Signal:** Rule file uses `.rule.md`, `.mdx`, `.markdown`, or another non-`.md` extension

**CHANGE:** Rename to `.md`
**FROM:** `.claude/rules/api-handlers.rule.md`
**TO:** `.claude/rules/api-handlers.md`
**REASON:** Anthropic's discovery scans for `.md` files only. Other extensions are skipped.

### Malformed `paths:` Glob

**Signal:** `paths:` is present but a glob has unmatched brackets, invalid wildcards, or empty pattern

**CHANGE:** Repair the glob syntax
**FROM:** `paths: "src/api/**/*.{ts"` (unclosed brace)
**TO:** `paths: "src/api/**/*.{ts,tsx}"`
**REASON:** Malformed globs silently fail to match — the rule is in the file but Claude never loads it for any real file path.

### File Too Large

**Signal:** File exceeds 200 non-blank lines

**CHANGE:** Split into topic-specific files
**FROM:** `.claude/rules/conventions.md` (350 lines covering API + tests + deploy)
**TO:** `.claude/rules/api-conventions.md` + `.claude/rules/test-conventions.md` + `.claude/rules/deploy-conventions.md`
**REASON:** Anthropic's CLAUDE.md guidance — "longer files consume more context and reduce adherence" — applies to rules. Splitting also improves the on-demand load path for path-scoped rules.

### Unknown Frontmatter Key

**Signal:** Frontmatter contains top-level keys other than `paths:`

**CHANGE:** Remove the unknown key, or move its content into the body
**FROM:**
```yaml
---
paths:
  - "src/api/**/*.ts"
severity: warn
description: API conventions
---
```
**TO:**
```yaml
---
paths:
  - "src/api/**/*.ts"
---

# API Conventions
```
**REASON:** Anthropic documents only `paths:` in rule frontmatter. Other keys (`severity:`, `description:`, `name:`, `type:`) are not consumed by Claude Code and add maintenance noise without behavioral effect.

---

## Tier 2 — Dimension 1: Specificity

### Anchor-Free Directive

**Signal:** Directive uses anchor-free terms ("good", "clean", "clear", "appropriate", "well-structured", "properly", "nice", "consistent") without a verifiable definition

**CHANGE:** Replace each anchor-free term with a verifiable directive
**FROM:** "Format code properly and keep files organized"
**TO:** "Use 2-space indentation; run `prettier --check` before committing. API handlers live in `src/api/handlers/`."
**REASON:** Anthropic's example: *"'Use 2-space indentation' instead of 'Format code properly'"*. Anchor-free directives produce uneven adherence because two readers (or two Claude sessions) can interpret them differently.

### Reader-Defers Directive

**Signal:** Directive defers the decision back to the reader without a fallback rule ("use your judgment", "as appropriate", "where it makes sense")

**CHANGE:** Either remove the deferred directive (it carries no information) or add the fallback rule
**FROM:** "Use TypeScript strict mode where it makes sense"
**TO:** "Use TypeScript strict mode in all files under `src/`. Exception: generated code in `src/codegen/`."
**REASON:** A directive that doesn't tell Claude what to do isn't a rule. Either commit to the directive or remove it.

---

## Tier 2 — Dimension 2: Single Concern

### Multiple Topics in One File

**Signal:** Multiple top-level `##` sections cover distinct topics that wouldn't naturally co-evolve

**CHANGE:** Split into separate topic files
**FROM:** `.claude/rules/conventions.md` with sections "API design", "Test naming", "Deployment process"
**TO:** `.claude/rules/api-design.md` + `.claude/rules/test-naming.md` + `.claude/rules/deployment.md`
**REASON:** One topic per file. Each rule should answer one question — "how do we do X?" Mixing topics makes path-scoping impossible (each topic might apply to different files) and grows the file beyond the size guidance.

### Body Doesn't Match Filename

**Signal:** Filename describes one topic but body covers another in addition

**CHANGE:** Move the off-topic content to a file matching its actual topic
**FROM:** `api-design.md` containing API conventions AND a section on commit message format
**TO:** `api-design.md` (API only) + `commit-messages.md` (or move into `.claude/CLAUDE.md` if it's a project-wide standard)
**REASON:** Filename is the discovery handle. Future maintainers grep for `commit-messages.md` when looking for commit conventions; they don't expect to find them inside `api-design.md`.

### `paths:` Union Covers Distinct Topics

**Signal:** `paths:` is a union of unrelated patterns where each `##` section applies to only one of them

**CHANGE:** Split the rule so each file's `paths:` covers only the directives in that file
**FROM:**
```yaml
---
paths:
  - "src/api/**/*.ts"
  - "tests/**/*.test.ts"
---
```
with separate API-section and test-section bodies
**TO:** Two files, one with `paths: "src/api/**/*.ts"` and one with `paths: "tests/**/*.test.ts"`
**REASON:** Path-scoping wastes effort if Claude loads the API section when reading test files (and vice versa). Splitting halves the loaded context and tightens the rule's relevance.

---

## Tier 3: Conflicts

**Signal:** Following one rule's directives as written would cause a developer to violate another rule

Resolution strategies in preference order:

1. **Narrow scope** — if one rule was over-broad (always-on when it should be path-scoped, or paths-glob too wide), narrow it so the two rules no longer co-fire on the same files. Verify the narrowed scope still covers the cases the rule was added for.

2. **Merge** — if two rules enforce complementary aspects of the same convention, merge into one rule with both directives stated together. Verify the merged file still passes the size and single-concern checks.

3. **Explicit boundary** — add an exception to one rule acknowledging the other: "Exception: in files covered by `[other-rule.md]`, [behavior] is acceptable." This preserves both rules without contradiction.

4. **Deprecate one** — if one rule supersedes the other: delete the older file. (Anthropic doesn't define an `archived:` status for rules; deletion is the canonical retirement.)

**Intent-preservation check for conflict resolution:** Confirm the resolution preserves the behavioral intent of both rules, not just one. A resolution that silently retires one rule's directive must be flagged for human review.
