---
name: Naming & Structure
description: Public target names are kebab-case verbs; internal helpers are `_`-prefixed; targets are grouped by lifecycle with section comments; `.PHONY` mirrors the public surface.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Naming & Structure

A Makefile's public target list is the project's command palette. Naming and grouping are load-bearing documentation: muscle memory for `make test` / `make build` / `make lint` works across repos only when names follow the shell-command convention, and a contributor scanning a Makefile for "what can I run here" needs the public verbs visually separated from the helpers.

## What to look for

- Target names that aren't kebab-case verbs: `runTheTests:`, `do_stuff:`, `Deploy:`, `format-the-python-code:`.
- Helper targets (used only as prerequisites, no `## description`) without a `_` prefix — they pollute `make help` and the public surface.
- Public and helper targets interleaved with no grouping or section comments (`# --- Test ---`, `# --- Deploy ---`).
- A `.PHONY` list that doesn't mirror the public surface — 30 entries when there are 40 phony verbs, or 40 entries when there are only 30 (drift in either direction).
- Verb-pair inconsistencies (`lint` and `lint-py` adjacent to `test` and `pytest` — pick one convention).
- Sections out of lifecycle order (`deploy` before `build` before `test`).

## Severity

`warn` — naming is coaching, not blocking. The targets work; they're just harder to remember and harder to scan.

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 47, "context": "runTheTests:\\n\\tpytest\\n\\ncheck-deps:"},
  "reasoning": "`runTheTests` uses camelCase, breaking the shell-command convention readers expect (`make test` / `make build`). And `check-deps` is used only as a prerequisite for `test` but lacks the `_` prefix that signals 'internal helper, not part of the public API' — so it shows up in `make help` next to the public verbs.",
  "recommended_changes": "Rename to the shell-command convention and prefix the helper. Group by lifecycle with section comments:\n\n# --- Test ---\ntest: _check-deps ## Run the test suite.\n\t$(PYTHON) -m pytest\n_check-deps:\n\t@command -v pytest >/dev/null || { echo 'pytest missing' >&2; exit 1; }"
}
```

## Recipe (canonical guidance)

**CHANGE** Rename targets to the shell-command convention; group by lifecycle with section comments; prefix internal helpers with `_`.

**FROM**
```makefile
runTheTests:
check-deps:
Deploy:
```

**TO**
```makefile
# --- Test ---
test: _check-deps
_check-deps:
# --- Deploy ---
deploy: _check-deps
```

**REASON** Consistent naming and grouping is the load-bearing documentation of a Makefile. PascalCase and camelCase break muscle memory; scattered helpers mixed with public targets obscure the public API. Section comments give a reader a 30-second tour of the file.
