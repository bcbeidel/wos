---
name: Hook Structure
description: Every hook carries explicit `id` + human-readable `name`; local hook logic lives in `scripts/hooks/` not inline `entry:` shell; no reimplementation of built-in `pre-commit-hooks`.
paths:
  - "**/.pre-commit-config.yaml"
  - "**/.pre-commit-config.yml"
---

Every hook carries explicit `id` + human-readable `name`; local hook logic lives in `scripts/hooks/` not inline `entry:` shell; no reimplementation of built-in `pre-commit-hooks`.

**Why:** Hook structure determines reviewability — *Explicit `id` + human-readable `name`*, *Custom hook logic in `scripts/hooks/`*, *No duplication of built-in `pre-commit-hooks`*. Inline shell in YAML (`entry: 'bash -c "find ... | xargs grep -q foo && echo ok"'`) is unreviewable, untestable, and silently broken-by-quoting. An unnamed hook produces opaque failure output (developers see the `id:` instead of a descriptive label). Local reimplementations of upstream `pre-commit-hooks` (trailing-whitespace, EOF-fixer, merge-conflict, large-file) are pure tech debt — they drift, miss edge cases, and consume maintenance effort.

**How to apply:** Confirm every hook (especially `repo: local`) has both `id:` and a human-readable `name:`. Confirm every local-hook `entry:` is a single command or a script file path — no `&&` / `||` / `|` / `;` / `$(...)` / `bash -c`. Extract any inline shell complexity into `scripts/hooks/<id>.sh`. Confirm no local hook reimplements an upstream `pre-commit-hooks` check; replace with the upstream original.

```yaml
  - repo: local
    hooks:
      - id: validate-schema
        name: validate jsonschema contract
        entry: scripts/hooks/validate_schema.py
        language: python
        files: ^schemas/.*\.json$
```

**Common fail signals (audit guidance):** A local hook with `entry: 'bash -c "find ... | xargs grep -q foo && echo ok"'` (inline complexity); `id: check-trailing-whitespace` as a local hook when the upstream `trailing-whitespace` is already available.
