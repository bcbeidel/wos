---
name: Shared References Registry
description: Passive catalog of shared reference files under plugins/build/_shared/references/. Maps slug to file path and lists the build-*/check-* skills that declare each file in their `references:` frontmatter. Not loaded at skill invocation — consult manually when adding or retiring a consumer.
---

# Shared References Registry

Passive catalog of shared reference files used across `build-*` / `check-*`
skills. **Not loaded at skill invocation** — consumers reference shared
files directly via relative paths in their SKILL.md `references:`
frontmatter. This registry exists to make the ownership graph visible
when adding a new consumer, retiring a file, or auditing drift.

When a consumer's `references:` entry is added or removed, update the
corresponding row's Consumers column in the same commit.

## Catalog

| Slug | File | Consumers |
|------|------|-----------|
| `primitive-routing` | `primitive-routing.md` | `build-hook`, `build-rule`, `build-skill`, `build-subagent` |
| `rule-canonical-form` | `rule-canonical-form.md` | `build-rule`, `check-rule` |
| `rule-structured-intent` | `rule-structured-intent.md` | `build-rule`, `check-rule` |
| `rule-audit-rubric` | `rule-audit-rubric.md` | `check-rule` |
