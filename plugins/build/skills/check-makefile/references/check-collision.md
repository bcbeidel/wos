---
name: Cross-Makefile Collision
description: When the audit scope holds multiple Makefile / `*.mk` files, surface duplicated recipe boilerplate, divergent `SHELL` / `.SHELLFLAGS` assignments, or `help` defined in more than one file.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Cross-Makefile Collision

When a project's build is split across a top-level `Makefile` and one or more included `*.mk` files, structural drift between them is the early-warning sign that the split has outgrown its coordination. This dimension activates only when the audit scope holds multiple Makefile artifacts; single-file scope returns `inapplicable` silently.

## What to look for

- A `*.mk` file that re-defines `SHELL` or `.SHELLFLAGS`, overriding (or contradicting) the top-level pin.
- Duplicate `.PHONY` lists that include the same target across more than one file (drift hazard — adding to one and forgetting the other).
- `help` defined in more than one Makefile (only the top-level one is actually invoked; the others are dead code).
- Identical recipe boilerplate (a 6-line `_check-deps:` recipe, the same `awk` `help`-parser) repeated verbatim across siblings — a candidate for a `mk/common.mk` include.
- Divergent assignment-operator conventions (`PYTHON := python3` in one `*.mk`, `PYTHON ?= python3` in another) that cause confusing override behavior.

## Severity

`warn` — the audit surfaces the duplication candidate; the maintainer decides whether to hoist. Most cases are coaching; an actively contradictory `SHELL` override may rise to `fail` at the judge's discretion.

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 3, "context": "mk/test.mk: SHELL := /bin/sh"},
  "reasoning": "Top-level `Makefile` pins `SHELL := bash` (line 4) but `mk/test.mk:3` overrides it to `/bin/sh`. Included files inherit the top-level configuration; resetting it silently breaks pipelines that depend on bash features (pipefail, `[[ ]]`).",
  "recommended_changes": "Remove the SHELL line from mk/test.mk and inherit from the top-level Makefile:\n\n# mk/test.mk\n# (no SHELL assignment — inherits SHELL := bash from Makefile)\n\nIf a section genuinely needs a different shell, name it explicitly (a target-local override) and document why."
}
```

## Recipe (canonical guidance)

**CHANGE** Move the canonical definition (`SHELL`, `.SHELLFLAGS`, `help`) to the top-level Makefile. Keep included `*.mk` files scoped to their lifecycle section — `.PHONY` additions are fine, re-defining `SHELL` is not. Hoist duplicated recipe bodies to a shared `mk/common.mk` include.

**FROM** `mk/test.mk` with `SHELL := /bin/sh` (overrides the top-level `SHELL := bash`).
**TO** Remove the `SHELL` line from `mk/test.mk`; inherit from `Makefile`.

**REASON** Included files inherit the top-level configuration. A `mk/test.mk` that resets `SHELL` silently breaks pipelines that depend on bash features. Drift across included files is the early warning that the Makefile split has outgrown its coordination — a single source of truth (top-level `Makefile` for shell pins, one `help` definition, shared boilerplate in `mk/common.mk`) is the durable fix.
