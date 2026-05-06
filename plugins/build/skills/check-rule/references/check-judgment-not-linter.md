---
name: Judgment Not Linter
description: Reserve rules for semantic conventions a tool can't catch — delete rules that restate a formatter, linter, or type-checker.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

Reserve rule files for semantic conventions a formatter, linter, or type-checker can't express. When a check is mechanically enforceable, configure the tool — not the rule.

**Why:** Deterministic checks belong in tooling. Tooling catches violations at edit-time and CI-time deterministically; a rule only catches them when Claude happens to re-read the file, and even then unreliably. Worse, a rule restating a formatter's job dilutes the authority of rules that genuinely need judgment — readers who learn to skim past trivial style rules also skim past the load-bearing ones. Type-checker violations produce build failures; a rule cannot compete with that enforcement strength.

**How to apply:** When a rule enforces whitespace, indentation, or quote style, delete it and ensure `.prettierrc` (or equivalent) encodes the settings and runs in CI / pre-commit. When a rule enforces import ordering or unused-import removal, delete it and configure `ruff` / `eslint`. When a rule mandates type annotations, delete it and enable `--strict` (TypeScript) or `--disallow-untyped-defs` (mypy). The rules that survive encode semantic conventions no tool can express ("staging models only cast, rename, dedupe") or judgment calls a reviewer would make that a linter wouldn't ("error messages name the failing operation and the input that caused it").

```markdown
Staging models only cast, rename, and dedupe.
Reshaping logic belongs in intermediate or mart layers.
```

**Common fail signals (audit guidance):**
- Rule enforces whitespace/indentation/quote-style (formatter's job)
- Rule enforces import sorting or unused-import removal (linter/tooling job)
- Rule enforces type annotations that a type-checker would catch
- Rule restates a conventional-commits / commitlint / prettier rule
