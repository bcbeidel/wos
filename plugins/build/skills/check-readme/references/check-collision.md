---
name: Cross-README Collision
description: When the audit scope holds multiple READMEs, surface near-identical install / contributing / license boilerplate that could be hoisted to a shared docs page or org-level default.
paths:
  - "**/README.md"
  - "**/Readme.md"
---

When multiple READMEs in related projects (a monorepo scan) share near-identical install, contributing, or license boilerplate, surface the duplication so a maintainer can hoist it to a single source of truth.

**Why:** Cross-repo duplication is a slower-moving form of *Link to detailed docs rather than duplicating* — the same anti-pattern that produces 800-line per-package READMEs produces twelve-package monorepos with the same install steps repeated twelve times. Duplication silently diverges; one project's install doc gets a fix, the others don't, and readers landing in different repos see contradictory guidance. A single source of truth — an org-level `.github/profile/README.md`, a shared docs site, or a snippet file — is the only durable fix. Severity is `warn`: the audit surfaces the candidate, the maintainer decides whether to hoist.

**How to apply:** Activate this rule only when the audit scope holds multiple READMEs (single-artifact scope returns `inapplicable` silently). Identify content blocks (install steps, contributing language, license sections) that appear near-identically across two or more files. Surface the highest-signal candidate — the block whose duplication has the most projects and the most lines — with concrete file paths and line ranges. If found, hoist the shared content to a common location (org-level `.github/profile/README.md`, shared docs site, or snippet file) and link from the per-project READMEs.

```markdown
<!-- packages/foo/README.md, packages/bar/README.md, packages/baz/README.md -->
## Contributing
See the [monorepo contributing guide](../../CONTRIBUTING.md).
```

**Common fail signals (audit guidance):** Identical Installation sections across three or more sibling READMEs; verbatim Contributing prose duplicated in every package; License section copy-pasted across repos in an org-wide scan. Severity: `warn` — the audit surfaces the candidate; the maintainer decides whether to hoist.
