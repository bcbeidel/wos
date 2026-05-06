---
name: Scope Tightness
description: Match `paths:` breadth to content breadth — no unscoped rules naming a specific directory; no `paths:` wider than the rule warrants.
paths:
  - "**/.claude/rules/*.md"
  - "**/.claude/rules/**/*.md"
---

Make `paths:` match the breadth of the rule's actual content. Project-wide rules can omit `paths:`; rules that name a specific directory, file extension, or module must scope to it.

**Why:** An unscoped rule is a context tax on every unrelated task — Claude loads it for work where it doesn't apply, consuming budget. A `paths:` glob wider than the content warrants makes the rule fire when it shouldn't (e.g., `paths: "**/*"` for a TypeScript-only rule loads it for every Markdown edit). Both failure modes silently degrade context efficiency without producing visible errors, so they accumulate over time.

**How to apply:** When the rule body begins "For React components…" or "In API handlers…" but has no frontmatter, add `paths:` matching the content's actual reach (`paths: "src/components/**/*.tsx"`). When `paths: "**/*"` covers a TypeScript-only rule, narrow to `paths: "**/*.{ts,tsx}"`. Verify the narrowed scope still covers every file the rule was added for. A justified always-on rule (project-wide standard with no directory-specific language) keeps `paths:` absent.

```markdown
---
paths:
  - "src/components/**/*.tsx"
---

# React Component Conventions

Use named exports for components...
```

**Common fail signals (audit guidance):**
- Rule is always-on (no `paths:`) but content names a specific directory, file extension, or module (e.g., rule text mentions "React components" or "API handlers" without a corresponding `paths:`)
- `paths:` glob is wider than the content warrants (e.g., `paths: "**/*"` for a rule that applies only to TypeScript files)

**Exception:** Project-wide standards whose content applies everywhere correctly omit `paths:` — always-on is the right scope when nothing in the body names a specific directory or file type.
