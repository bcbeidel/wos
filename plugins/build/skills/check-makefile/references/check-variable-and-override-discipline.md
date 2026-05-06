---
name: Variable & Override Discipline
description: Assignment operators (`?=`, `:=`, `=`) reflect intent; tool invocations are pinned to project-local versions; expensive `$(shell …)` does not run at parse time.
type: judgment-rule
related:
  - ../SKILL.md
  - ../../../_shared/references/makefile-best-practices.md
---

# Variable & Override Discipline

Make has three top-level assignment operators that look interchangeable and aren't. `:=` evaluates immediately; `?=` lets the environment override; `=` re-evaluates on every reference (a footgun when the right-hand side has a `$(shell …)`). This dimension judges whether the file uses each operator deliberately, whether configuration is overridable, and whether tool invocations are pinned to the project's local copy.

## What to look for

- Bare `=` at the top level without a `# deferred:` / `# recursive:` annotation explaining why deferred evaluation is intentional.
- User-configurable values not factored into `?=` (a hardcoded `PYTHON := python3` instead of `PYTHON ?= python3`, blocking environment override).
- Tool invocations as bare command names that rely on `$PATH` (`pytest`, `ruff`, `eslint`) instead of project-local pins (`.venv/bin/pytest`, `./node_modules/.bin/eslint`).
- Top-level `$(shell expensive-command …)` that runs every time `make` is invoked (including `make help`).
- Hardcoded version tags like `:latest` that drift over time.
- Configuration variables interleaved with target definitions instead of grouped at the top.

## Severity

`warn` — these are reproducibility and ergonomics concerns. The Makefile works; it's just brittle to environment drift.

## Example finding

```json
{
  "status": "warn",
  "location": {"line": 23, "context": "test:\\n\\tpytest"},
  "reasoning": "The `test` target invokes bare `pytest`, which uses whatever pytest is first on $PATH — the global one, often a version mismatch with the project's pinned dev deps. CI and local can run different code without warning.",
  "recommended_changes": "Pin the tool to the project-local copy via a `?=` override at the top:\n\nPYTHON ?= .venv/bin/python\n\ntest: ## Run the test suite.\n\t$(PYTHON) -m pytest\n\nThe `?=` lets CI override (CI ?= 1 PYTHON=python3) without editing the Makefile."
}
```

## Recipe (canonical guidance)

**CHANGE** Factor configurable values into `?=` overrides at the top. Use `.venv/bin/` / `./node_modules/.bin/` for tool invocations.

**FROM** `test:\n\tpytest`
**TO**
```makefile
PYTHON ?= .venv/bin/python

test:
	$(PYTHON) -m pytest
```

**REASON** Bare `pytest` uses whatever `pytest` is first on `$PATH` — often the global one, sometimes a version mismatch. Pinning to `.venv/bin/python` keeps CI and local identical. `?=` allows environment override without editing the Makefile.
