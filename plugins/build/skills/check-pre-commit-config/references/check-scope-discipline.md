---
name: Scope Discipline
description: Scope every hook to the files it actually processes via `files:` / `types:` / `types_or:`, exclude generated/vendored paths, and justify every `pass_filenames: false`.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

**Why:** Hook scope governs cost — *Hooks scoped to changed files*, *Default to `pass_filenames: true`*, *Exclude generated and vendored directories*. Unscoped hooks run on every staged file (paying full cost on every commit) and frequently report pre-existing issues in vendored or generated content the developer didn't touch. Both drive bypass culture: the gate becomes noisy enough that developers reach for `--no-verify`, and the gate stops gating.

**How to apply:** Confirm every `repo: local` hook declares `files:` / `types:` / `types_or:`. Confirm the repo-wide `exclude:` regex covers vendored and generated directories actually present in this repo (`vendor/`, `node_modules/`, `dist/`, `.terraform/`, generated protos). Confirm any `pass_filenames: false` carries an adjacent `# justified:` comment naming the cross-file invariant that requires repo-wide scanning.

```yaml
  - repo: local
    hooks:
      - id: validate-schema
        name: validate jsonschema contract
        entry: scripts/hooks/validate_schema.py
        files: ^schemas/.*\.json$
        language: python
```

**Common fail signals (audit guidance):** A local hook with no `files:` / `types:` (runs on every staged file regardless of relevance); `pass_filenames: false` without justification (the tool is probably framework-correct to run per-file).
