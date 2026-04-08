---
name: check-rules
description: >
  Validates files against project rules defined in docs/rules/. Use when
  the user wants to "check rules", "enforce rules", "validate against
  rules", "run rule checks", or "are my files compliant".
argument-hint: "[file path, directory, or blank for git-changed files]"
user-invocable: true
references:
  - references/evaluation-prompt.md
  - references/hook-setup.md
---

# /wos:check-rules

Evaluate files against project rules in `docs/rules/`. Each rule is
matched by scope glob, then evaluated semantically by Claude using the
locked rubric pattern — one rule, one file, one verdict.

## Workflow

### 1. Discover Rules

Read all `*.rule.md` files in `docs/rules/`. Parse frontmatter to
extract `name`, `scope`, and `severity` for each rule.

If no rules exist, inform the user: "No rules found in `docs/rules/`.
Use `/wos:extract-rules` to create your first rule."

### 2. Determine Target Files

Based on the user's input:

| Input | Behavior |
|-------|----------|
| Specific file path | Check that file only |
| Directory path | Check all files in that directory (recursive) |
| Glob pattern | Check matching files |
| No input | Check git-changed files: `git diff --name-only HEAD` plus untracked files from `git ls-files --others --exclude-standard` |

### 3. Match Rules to Files

For each target file, find rules whose `scope` glob matches the file
path (relative to project root). A rule with multiple scope patterns
matches if ANY pattern matches.

Skip files with no matching rules — report nothing for them.

### 4. Evaluate Compliance

For each matched rule-file pair, evaluate compliance using the
[evaluation prompt](references/evaluation-prompt.md):

1. Read the full rule file (verbatim — never summarize)
2. Read the target file
3. Reason through compliance (chain-of-thought)
4. Produce a binary PASS/FAIL verdict with explanation

Evaluate each pair independently. Do not batch multiple rules into a
single evaluation — research shows independent evaluation produces
more reliable results.

### 5. Report Results

Group results by file. Format:

```
PASS  models/staging/orders.sql — Staging layer purity
FAIL  models/staging/customers.sql — Staging layer purity
  "Contains revenue calculation logic (line 12) — move to marts layer"
WARN  src/api/handler.py — Input validation required
  "No input validation before database query on line 34"
```

Use `FAIL` for rules with `severity: fail`, `WARN` for `severity: warn`.

After the file-by-file report, provide a summary:

```
3 files checked, 2 rules evaluated
1 pass, 1 fail, 1 warn
```

## Key Instructions

- The full rule file is included verbatim in each evaluation. Never
  summarize, paraphrase, or abbreviate the rule. The rule IS the rubric.
- Produce chain-of-thought reasoning BEFORE the verdict. Structured
  reasoning before judgment improves accuracy by 10-15 percentage points.
- One rule, one file, one verdict. Never evaluate multiple rules in a
  single pass — this degrades accuracy for all rules.
- When a file fails, cite the specific lines or patterns that violate
  the rule. Vague explanations ("doesn't follow the convention") are
  not actionable.
- If a target file is binary, empty, or cannot be meaningfully evaluated
  against the rule, report PASS with a note: "File type not applicable
  to this rule."

## Anti-Pattern Guards

1. **Summarizing rules** — include the full rule file verbatim. Summaries
   cause interpretation drift across evaluations.
2. **Batching evaluations** — evaluate each rule-file pair independently.
   Multi-rule prompts degrade all rules due to instruction limits.
3. **Vague failure explanations** — cite specific lines and patterns.
   "Doesn't comply" is not actionable feedback.
4. **Checking files with no matching rules** — skip silently. Don't
   report "no rules apply" for every unmatched file.
